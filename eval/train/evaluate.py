#!/usr/bin/env python3
"""Visible train evaluator for the temporal 3DGS sorting gym.

Scenes are generated from the public seeds below; the hidden test uses the same
generator family, hardware model and protocol with different scenes.

The evaluator generates every scene itself, starts each registered method
(``policies/<name>.json`` -> ``{"command": [...]}``, run from the repository
root) once per scene, and drives it frame by frame through a JSON-lines
protocol on stdin/stdout.  The method never sees Gaussian ids, depths or
orders.  It only decides which sorting-engine operations to run; the evaluator
executes them on its own memory model, counts their DRAM traffic, rasterizes
sampled pixels of every tile in the resulting order and compares them with the
exactly sorted rendering.  A built-in exact full re-sort (``full_sort``) is the
fixed baseline.

Protocol (one line per message)
  -> {"type": "scene", "tiles_x", "tiles_y", "capacity", "merge_fanin",
       "feedback_block", "max_ops_per_tile"}
  -> {"type": "frame", "frame": t, "tiles": [info, ...]}       (t = 1, 2, ...)
  <- {"ops": [[op, ...], ...]}                     (one op list per tile)
  -> {"type": "end"}

  Frame 0 is not sent: every method starts from the same exactly sorted
  tables.  ``info`` per tile: N Gaussians in the tile now; L entries in the
  stored table; I incoming Gaussians (in the tile now but not valid in the
  table); X invalid entries (left the tile at the previous frame); ``inv``
  number of depth inversions the rasterizer met in each block of
  ``feedback_block`` table positions at the previous frame; ``drift`` mean
  depth change of reused entries at the previous frame's depth write-back.

Operations (executed in order, costs in 8-byte table-entry accesses)
  {"op": "regen"}  first op only.  Preprocessing rewrites the whole tile
      table (current Gaussians, current depths, Gaussian-id order): N writes.
      Without it, preprocessing writes only the incoming table: I writes.
  {"op": "pass", "start": a, "end": b, "cuts": [...], "sort": true,
    "merge": false, "refresh": false, "offset": 0.0}
      One streaming pass over table[a:b): every segment between consecutive
      cuts (at most ``capacity`` entries when sorting) is sorted on chip by its
      stored depth.  refresh=true first replaces stored depths by current ones
      (+ (b - a) random reads).  merge=true (whole table, once per frame) also
      merges the incoming Gaussians, sorted by current depth + offset, into the
      stream and drops invalid entries: L + I reads and L' writes (+ extra
      passes to sort more than ``capacity`` incoming).  Otherwise 2 (b - a).
  {"op": "merge_runs", "start": a, "end": b, "cuts": [...]}
      Merges at most ``merge_fanin`` consecutive runs: 2 (b - a).
  After the operations the tile is rasterized in table order (entries not in
  the tile are skipped) and the rasterizer writes current depths and valid
  bits back into the table for free (deferred depth update).

Scored per experiment: traffic_reduction_pct versus full_sort (higher is
better), psnr_drop_db of the rendering (lower is better) and
mean_abs_rank_error (lower is better).  A crash, timeout (120 s per response,
600 s per scene), malformed response, illegal operation, missing scene or a psnr_drop_db above the experiment's
quality limit fails the method, which then receives the worst value of every
metric in every experiment.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import heapq
import json
import math
import multiprocessing
import os
import random
import select
import subprocess
import sys
import time
from operator import itemgetter
from pathlib import Path

# ---------------------------------------------------------------------------
# Fixed rendering / hardware model
# ---------------------------------------------------------------------------
TILE_PX = 64
IMAGE_W = 768
IMAGE_H = 448
FOCAL_PX = 650.0
TILES_X = IMAGE_W // TILE_PX
TILES_Y = IMAGE_H // TILE_PX
NUM_TILES = TILES_X * TILES_Y
NEAR_Z = 0.3
CAPACITY = 256           # on-chip sorting window (entries)
MERGE_FANIN = 2          # runs per merge_runs op (two-input merge unit, MSU+)
FEEDBACK_BLOCK = 64      # table positions per inversion-feedback counter
ENTRY_BYTES = 8          # 32-bit Gaussian id + 32-bit depth
MAX_OPS_PER_TILE = 128
SAMPLES_PER_AXIS = 4
ALPHA_MIN = 1.0 / 255.0
ALPHA_MAX = 0.99
T_MIN = 1e-4
FPS = 30.0
KEY = itemgetter(1)



# ---------------------------------------------------------------------------
# Split configuration
# ---------------------------------------------------------------------------
SPLIT = "train"
REPO = Path(__file__).resolve().parents[2]
BASELINE_NAME = "full_sort"
FRAMES = 31              # frame 0 seeds the tables; frames 1..30 are scored (30 FPS)
BASE_SPEED = 3.0           # camera speed whose temporal statistics match the paper's Fig. 6/7
RAPID_FACTOR = 2.0         # the paper's rapid-camera-movement study (Fig. 17b) uses 2x-16x
EXPERIMENTS = {
    "synthetic_temporal_sorting": {"speed": BASE_SPEED, "scenes": [101, 102]},
    "rapid_camera_motion": {"speed": BASE_SPEED * RAPID_FACTOR, "scenes": [201, 202]},
}
# Mean PSNR of the original 3DGS reconstructions in the paper's Table 2; the
# ordering error is reported as the PSNR drop it causes at that level.
RECON_PSNR_DB = 26.87
RECON_MSE = 10.0 ** (-RECON_PSNR_DB / 10.0)
# Rendering-quality constraint (paper: < 0.1 dB degradation under normal motion).
GATE_MAX_PSNR_DROP_DB = {"synthetic_temporal_sorting": 0.1, "rapid_camera_motion": 1.0}
RANGES = {
    "traffic_reduction_pct": (-100.0, 100.0),
    "psnr_drop_db": (0.0, 10.0),
    "mean_abs_rank_error": (0.0, 500.0),
}
# Worst value of each metric, given to every metric of every experiment of a failed
# run.  A run whose psnr_drop_db exceeds the experiment's quality limit fails, so
# the limit is the worst psnr_drop_db a scored run can have.
WORST = {exp: {"traffic_reduction_pct": -100.0, "psnr_drop_db": GATE_MAX_PSNR_DROP_DB[exp],
               "mean_abs_rank_error": 500.0} for exp in EXPERIMENTS}
RESPONSE_TIMEOUT_S = 120.0
# Total time a method may spend answering over one scene (30 frames).  The
# reference answers in milliseconds; this only stops a method from stalling
# the evaluation until the job is killed and no score is written at all.
SCENE_BUDGET_S = 600.0
MAX_RESPONSE_BYTES = 32 * 1024 * 1024

# ---------------------------------------------------------------------------
# Scene and trajectory
# ---------------------------------------------------------------------------
def _clip01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def generate_scene(seed: int, density: float = 1.0) -> dict:
    """Procedural street-like Gaussian scene (isotropic 3D Gaussians)."""
    rng = random.Random(seed)
    half_w = rng.uniform(4.5, 7.0)
    height = rng.uniform(7.0, 12.0)
    z_min, z_max = 0.8, 85.0
    gx, gy, gz, gs, go, gr, gg, gb = [], [], [], [], [], [], [], []

    def z_sample() -> float:
        return z_min * (z_max / z_min) ** rng.random()

    def opacity() -> float:
        if rng.random() < 0.72:
            return 0.55 + 0.44 * rng.betavariate(2.0, 1.2)
        return 0.03 + 0.4 * rng.random()

    def add(x, y, z, s, base, tex):
        gx.append(x); gy.append(y); gz.append(z)
        gs.append(s * math.exp(rng.gauss(0.0, 0.35)))
        go.append(opacity())
        t = 0.12 * math.sin(tex[0] * x + tex[1] * y + tex[2] * z + tex[3])
        gr.append(_clip01(base[0] + t + rng.gauss(0, 0.06)))
        gg.append(_clip01(base[1] + t * 0.8 + rng.gauss(0, 0.06)))
        gb.append(_clip01(base[2] + t * 0.6 + rng.gauss(0, 0.06)))

    def rand_color():
        return (rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.9))

    def rand_tex():
        return (rng.uniform(0.5, 4.0), rng.uniform(0.5, 4.0), rng.uniform(0.5, 4.0), rng.uniform(0, 6.3))

    n_ground = int(26000 * density)
    base, tex = rand_color(), rand_tex()
    for _ in range(n_ground):
        z = z_sample()
        x = rng.uniform(-half_w - 1.0, half_w + 1.0)
        add(x, rng.gauss(0.0, 0.01), z, 0.05 + 0.012 * z, base, tex)

    for side in (-1.0, 1.0):
        base, tex = rand_color(), rand_tex()
        n_wall = int(17000 * density)
        for _ in range(n_wall):
            z = z_sample()
            y = rng.uniform(0.0, height)
            relief = 0.25 * math.sin(1.3 * z + 0.7 * y) + rng.gauss(0.0, 0.03)
            add(side * (half_w + relief), y, z, 0.05 + 0.011 * z, base, tex)

    n_obj = rng.randint(35, 55)
    for _ in range(n_obj):
        cx = rng.uniform(-half_w + 0.8, half_w - 0.8)
        cz = z_min * (z_max / z_min) ** (0.3 + 0.7 * rng.random())
        size = rng.uniform(0.35, 2.2)
        cy = size * rng.uniform(0.5, 1.4)
        base, tex = rand_color(), rand_tex()
        n = int((180 + 260 * size) * density)
        sphere = rng.random() < 0.5
        for _ in range(n):
            if sphere:
                u, v = rng.uniform(-1, 1), rng.uniform(0, 2 * math.pi)
                w = math.sqrt(max(0.0, 1 - u * u))
                px, py, pz = w * math.cos(v), u, w * math.sin(v)
            else:
                face = rng.randrange(3)
                a, b = rng.uniform(-1, 1), rng.uniform(-1, 1)
                sgn = 1.0 if rng.random() < 0.5 else -1.0
                px, py, pz = (sgn, a, b) if face == 0 else ((a, sgn, b) if face == 1 else (a, b, sgn))
            add(cx + px * size, max(0.0, cy + py * size), cz + pz * size, 0.03 + 0.04 * size, base, tex)

    n_tree = rng.randint(8, 14)
    for _ in range(n_tree):
        cx = (half_w - 0.6) * (1.0 if rng.random() < 0.5 else -1.0)
        cz = z_min * (z_max / z_min) ** (0.25 + 0.75 * rng.random())
        r = rng.uniform(1.0, 2.5)
        cy = rng.uniform(3.0, 5.0)
        base = (rng.uniform(0.05, 0.3), rng.uniform(0.35, 0.7), rng.uniform(0.05, 0.3))
        tex = rand_tex()
        for _ in range(int(900 * density)):
            px, py, pz = rng.gauss(0, 0.5), rng.gauss(0, 0.6), rng.gauss(0, 0.5)
            add(cx + px * r, cy + py * r, cz + pz * r, 0.08, base, tex)

    base, tex = rand_color(), rand_tex()
    for _ in range(int(3000 * density)):
        add(rng.uniform(-half_w, half_w), rng.uniform(0, height * 1.4), z_max + rng.uniform(0, 3), 0.9, base, tex)

    for _ in range(int(1500 * density)):
        add(rng.uniform(-half_w, half_w), rng.uniform(0.2, height), z_sample(), 0.06,
            (rng.random(), rng.random(), rng.random()), rand_tex())

    n = len(gx)
    ids = list(range(n))
    rng.shuffle(ids)  # Gaussian ids carry no spatial or depth information.
    traj = {
        "x0": rng.uniform(-1.0, 1.0),
        "speed": rng.uniform(0.9, 1.4),
        "yaw_amp": math.radians(rng.uniform(10.0, 20.0)),
        "yaw_freq": rng.uniform(0.15, 0.3),
        "yaw_phase": rng.uniform(0, 2 * math.pi),
        "pitch_amp": math.radians(rng.uniform(1.5, 4.0)),
        "pitch_freq": rng.uniform(0.2, 0.4),
        "pitch_phase": rng.uniform(0, 2 * math.pi),
        "sway_amp": rng.uniform(0.15, 0.4),
        "sway_freq": rng.uniform(0.2, 0.5),
        "sway_phase": rng.uniform(0, 2 * math.pi),
        "bob_phase": rng.uniform(0, 2 * math.pi),
    }
    return {"x": gx, "y": gy, "z": gz, "s": gs, "o": go, "r": gr, "g": gg, "b": gb, "id": ids, "traj": traj}


def camera_pose(traj: dict, frame: int, speed_factor: float) -> tuple:
    tau = frame / FPS * speed_factor
    two_pi = 2.0 * math.pi
    cx = traj["x0"] + traj["sway_amp"] * math.sin(two_pi * traj["sway_freq"] * tau + traj["sway_phase"])
    cy = 1.6 + 0.03 * math.sin(two_pi * 1.8 * tau + traj["bob_phase"])
    cz = traj["speed"] * tau
    yaw = traj["yaw_amp"] * math.sin(two_pi * traj["yaw_freq"] * tau + traj["yaw_phase"])
    pitch = traj["pitch_amp"] * math.sin(two_pi * traj["pitch_freq"] * tau + traj["pitch_phase"])
    return cx, cy, cz, yaw, pitch


def project_frame(scene: dict, pose: tuple) -> list:
    """Return per-tile member dicts: gid -> (depth, u, v, inv_two_sigma2, opacity, rgb)."""
    cx, cy, cz, yaw, pitch = pose
    cyaw, syaw = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    half_w, half_h = IMAGE_W * 0.5, IMAGE_H * 0.5
    f = FOCAL_PX
    tiles: list[dict] = [dict() for _ in range(NUM_TILES)]
    xs, ys, zs, ss, os_ = scene["x"], scene["y"], scene["z"], scene["s"], scene["o"]
    rs, gs, bs, ids = scene["r"], scene["g"], scene["b"], scene["id"]
    tx_max, ty_max = TILES_X - 1, TILES_Y - 1
    for i in range(len(xs)):
        dx, dy, dz = xs[i] - cx, ys[i] - cy, zs[i] - cz
        # yaw around +y, then pitch around +x (camera looks along +z)
        x1 = cyaw * dx - syaw * dz
        z1 = syaw * dx + cyaw * dz
        y2 = cp * dy - sp * z1
        z2 = sp * dy + cp * z1
        if z2 <= NEAR_Z:
            continue
        inv_z = 1.0 / z2
        u = half_w + f * x1 * inv_z
        v = half_h - f * y2 * inv_z
        sig = f * ss[i] * inv_z
        if sig < 0.3:
            sig = 0.3
        rad = 3.0 * sig
        if u + rad < 0 or u - rad >= IMAGE_W or v + rad < 0 or v - rad >= IMAGE_H:
            continue
        tx0 = int((u - rad) // TILE_PX)
        tx1 = int((u + rad) // TILE_PX)
        ty0 = int((v - rad) // TILE_PX)
        ty1 = int((v + rad) // TILE_PX)
        if tx0 < 0:
            tx0 = 0
        if ty0 < 0:
            ty0 = 0
        if tx1 > tx_max:
            tx1 = tx_max
        if ty1 > ty_max:
            ty1 = ty_max
        rec = (z2, u, v, 0.5 / (sig * sig), os_[i], rs[i], gs[i], bs[i])
        gid = ids[i]
        for ty in range(ty0, ty1 + 1):
            row = ty * TILES_X
            for tx in range(tx0, tx1 + 1):
                tiles[row + tx][gid] = rec
    return tiles


# ---------------------------------------------------------------------------
# Rendering (sampled pixels per tile)
# ---------------------------------------------------------------------------
_SAMPLE_OFFSETS = [(k + 0.5) * TILE_PX / SAMPLES_PER_AXIS for k in range(SAMPLES_PER_AXIS)]


def render_context(tile_idx: int, members: dict) -> list:
    """Per sample pixel: list of (gid, alpha, r, g, b) for Gaussians that touch it."""
    tx, ty = tile_idx % TILES_X, tile_idx // TILES_X
    xs = [tx * TILE_PX + o for o in _SAMPLE_OFFSETS]
    ys = [ty * TILE_PX + o for o in _SAMPLE_OFFSETS]
    n = SAMPLES_PER_AXIS
    pix: list[list] = [[] for _ in range(n * n)]
    log255 = math.log(255.0)
    x0, y0 = xs[0], ys[0]
    step = TILE_PX / SAMPLES_PER_AXIS
    for gid, rec in members.items():
        depth, u, v, k2, o, r, g, b = rec
        lo = math.log(o) + log255
        if lo <= 0.0:
            continue
        reff = math.sqrt(lo / k2)
        i0 = max(0, int(math.ceil((u - reff - x0) / step)))
        i1 = min(n - 1, int(math.floor((u + reff - x0) / step)))
        if i0 > i1:
            continue
        j0 = max(0, int(math.ceil((v - reff - y0) / step)))
        j1 = min(n - 1, int(math.floor((v + reff - y0) / step)))
        if j0 > j1:
            continue
        for j in range(j0, j1 + 1):
            dy2 = (ys[j] - v) ** 2
            base = j * n
            for i in range(i0, i1 + 1):
                a = o * math.exp(-k2 * ((xs[i] - u) ** 2 + dy2))
                if a < ALPHA_MIN:
                    continue
                if a > ALPHA_MAX:
                    a = ALPHA_MAX
                pix[base + i].append((gid, a, r, g, b))
    return pix


def composite(pix: list, rank: dict) -> list:
    out = []
    for contrib in pix:
        if not contrib:
            out.append((0.0, 0.0, 0.0))
            continue
        ordered = sorted((rank[c[0]], c) for c in contrib if c[0] in rank)
        t = 1.0
        cr = cg = cb = 0.0
        for _, (gid, a, r, g, b) in ordered:
            nt = t * (1.0 - a)
            if nt < T_MIN:
                break
            w = a * t
            cr += w * r
            cg += w * g
            cb += w * b
            t = nt
        out.append((cr, cg, cb))
    return out


# ---------------------------------------------------------------------------
# Memory machine
# ---------------------------------------------------------------------------
class ProtocolError(Exception):
    pass


def _int(v, name):
    if isinstance(v, bool) or not isinstance(v, int):
        raise ProtocolError(f"{name} must be an integer")
    return v


def _check_cuts(cuts, start, end, max_seg, name):
    if not isinstance(cuts, list):
        raise ProtocolError(f"{name}.cuts must be a list")
    prev = start
    for c in cuts:
        c = _int(c, f"{name}.cuts[]")
        if c <= prev or c >= end:
            raise ProtocolError(f"{name}.cuts must be strictly increasing inside (start, end)")
        if max_seg is not None and c - prev > max_seg:
            raise ProtocolError(f"{name}: segment longer than on-chip capacity {CAPACITY}")
        prev = c
    if max_seg is not None and end - prev > max_seg:
        raise ProtocolError(f"{name}: segment longer than on-chip capacity {CAPACITY}")
    return [start] + list(cuts) + [end]


def incoming_sort_cost(n_in: int) -> int:
    if n_in <= CAPACITY:
        return 0
    runs = math.ceil(n_in / CAPACITY)
    levels = 0
    while runs > 1:
        runs = math.ceil(runs / MERGE_FANIN)
        levels += 1
    return 2 * n_in * (1 + levels)


def execute_tile(table: list, members: dict, incoming_ids: list, ops) -> tuple[list, int, set]:
    """Execute one tile's op list.  Returns (new_table, traffic_entries, inserted_ids)."""
    if not isinstance(ops, list):
        raise ProtocolError("tile ops must be a list")
    if len(ops) > MAX_OPS_PER_TILE:
        raise ProtocolError(f"more than {MAX_OPS_PER_TILE} ops for one tile")
    traffic = 0
    inserted: set = set()
    regen_first = bool(ops) and isinstance(ops[0], dict) and ops[0].get("op") == "regen"
    if regen_first:
        traffic += len(members)
        table = [[gid, members[gid][0], True] for gid in sorted(members)]
        incoming_ids = []
        inserted = set(members)
    else:
        traffic += len(incoming_ids)  # preprocessing writes the incoming table
    merged_once = False
    for k, op in enumerate(ops):
        if not isinstance(op, dict):
            raise ProtocolError("each op must be an object")
        kind = op.get("op")
        if kind == "regen":
            if k != 0:
                raise ProtocolError("regen must be the first op of a tile")
            continue
        if kind == "pass":
            n = len(table)
            start = _int(op.get("start", 0), "pass.start")
            end = _int(op.get("end", n), "pass.end")
            if not (0 <= start <= end <= n):
                raise ProtocolError("pass range outside table")
            do_sort = op.get("sort", True)
            refresh = op.get("refresh", False)
            merge = op.get("merge", False)
            for flag, nm in ((do_sort, "sort"), (refresh, "refresh"), (merge, "merge")):
                if not isinstance(flag, bool):
                    raise ProtocolError(f"pass.{nm} must be a boolean")
            bounds = _check_cuts(op.get("cuts", []), start, end, CAPACITY if do_sort else None, "pass")
            seg = table[start:end]
            if refresh:
                traffic += end - start  # random per-Gaussian depth fetch from the feature table
                for e in seg:
                    rec = members.get(e[0])
                    if rec is not None:
                        e[1] = rec[0]
            if do_sort:
                for a, b in zip(bounds[:-1], bounds[1:]):
                    part = seg[a - start:b - start]
                    part.sort(key=KEY)
                    seg[a - start:b - start] = part
            if merge:
                if merged_once:
                    raise ProtocolError("incoming may be merged only once per frame")
                if start != 0 or end != n:
                    raise ProtocolError("a merging pass must cover the whole table")
                offset = op.get("offset", 0.0)
                scale = op.get("scale", 1.0)
                for val, nm in ((offset, "offset"), (scale, "scale")):
                    if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
                        raise ProtocolError(f"pass.{nm} must be a finite number")
                if scale <= 0:
                    raise ProtocolError("pass.scale must be positive")
                merged_once = True
                kept = [e for e in seg if e[2]]
                inc = sorted(([gid, members[gid][0], True] for gid in incoming_ids), key=KEY)
                out = []
                i = j = 0
                nk, ni = len(kept), len(inc)
                while i < nk and j < ni:
                    if kept[i][1] <= inc[j][1] * scale + offset:
                        out.append(kept[i]); i += 1
                    else:
                        out.append(inc[j]); j += 1
                if i < nk:
                    out.extend(kept[i:])
                if j < ni:
                    out.extend(inc[j:])
                traffic += n + ni + len(out) + incoming_sort_cost(ni)
                inserted.update(incoming_ids)
                table = out
            else:
                traffic += 2 * (end - start)
                table[start:end] = seg
            continue
        if kind == "merge_runs":
            n = len(table)
            start = _int(op.get("start", 0), "merge_runs.start")
            end = _int(op.get("end", n), "merge_runs.end")
            if not (0 <= start <= end <= n):
                raise ProtocolError("merge_runs range outside table")
            bounds = _check_cuts(op.get("cuts", []), start, end, None, "merge_runs")
            if len(bounds) - 1 > MERGE_FANIN:
                raise ProtocolError(f"merge_runs accepts at most {MERGE_FANIN} runs")
            runs = [table[a:b] for a, b in zip(bounds[:-1], bounds[1:])]
            table[start:end] = list(heapq.merge(*runs, key=KEY))
            traffic += 2 * (end - start)
            continue
        raise ProtocolError(f"unknown op {kind!r}")
    return table, traffic, inserted


def deferred_update(table: list, members: dict, inserted: set) -> tuple[list, list]:
    """Rasterization-side depth/valid write-back.

    Returns (inv_counts, fit): fit = [scale, offset] is the least-squares fit
    new_depth ~ scale * stored_depth + offset over reused entries, computed
    from accumulators the rasterizer can keep while it overwrites depths.
    """
    n = 0
    sx = sy = sxx = sxy = 0.0
    for e in table:
        rec = members.get(e[0])
        if rec is None:
            e[2] = False
        else:
            d = rec[0]
            if e[2] and e[0] not in inserted and e[1] != d:
                x = e[1]
                n += 1
                sx += x
                sy += d
                sxx += x * x
                sxy += x * d
            e[1] = d
            e[2] = True
    fit = [1.0, 0.0]
    if n >= 2:
        var = sxx - sx * sx / n
        a = (sxy - sx * sy / n) / var if var > 1e-12 * max(sxx, 1e-12) else 0.0
        if a > 0 and math.isfinite(a):
            fit = [a, (sy - a * sx) / n]
        else:
            fit = [1.0, (sy - sx) / n]
    elif n == 1:
        fit = [1.0, sy - sx]
    inv = [0] * ((len(table) + FEEDBACK_BLOCK - 1) // FEEDBACK_BLOCK)
    prev = None
    for pos, e in enumerate(table):
        if not e[2]:
            continue
        if prev is not None and prev > e[1]:
            inv[pos // FEEDBACK_BLOCK] += 1
        prev = e[1]
    return inv, fit


# ---------------------------------------------------------------------------
# Built-in full-sort baseline
# ---------------------------------------------------------------------------
def full_sort_ops(n_members: int) -> list:
    ops = [{"op": "regen"}]
    if n_members == 0:
        return ops
    cuts = list(range(CAPACITY, n_members, CAPACITY))
    ops.append({"op": "pass", "start": 0, "end": n_members, "cuts": cuts})
    runs = [0] + cuts + [n_members]
    while len(runs) > 2:
        new_runs = [0]
        for g in range(0, len(runs) - 1, MERGE_FANIN):
            grp = runs[g:g + MERGE_FANIN + 1]
            if len(grp) > 2:
                ops.append({"op": "merge_runs", "start": grp[0], "end": grp[-1], "cuts": grp[1:-1]})
            new_runs.append(grp[-1])
        runs = new_runs
    return ops

# ---------------------------------------------------------------------------
# Policy protocol (one subprocess per policy and scene, JSON lines on stdio)
# ---------------------------------------------------------------------------
class PolicyFailure(Exception):
    pass


class SubprocessPolicy:
    def __init__(self, name: str, command: list, log_dir: Path):
        self.name = name
        self.command = command
        self.log_dir = log_dir
        self.proc = None
        self.buf = b""
        self.log = None
        self.spent = 0.0

    def start(self, header: dict, scene_label: str) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log = open(self.log_dir / f"{self.name}.{scene_label}.stderr.log", "wb")
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = "0"
        env["PYTHONUNBUFFERED"] = "1"
        try:
            self.proc = subprocess.Popen(
                self.command, cwd=str(REPO), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self.log, env=env, bufsize=0,
            )
        except OSError as exc:
            raise PolicyFailure(f"could not start policy command: {exc}") from exc
        self.buf = b""
        self.spent = 0.0
        self._send({"type": "scene", **header})

    def _send(self, obj: dict) -> None:
        data = (json.dumps(obj, separators=(",", ":")) + "\n").encode()
        fd = self.proc.stdin.fileno()
        deadline = time.monotonic() + RESPONSE_TIMEOUT_S
        view = memoryview(data)
        while view:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise PolicyFailure("timed out while sending input to the policy")
            _, writable, _ = select.select([], [fd], [], remaining)
            if not writable:
                continue
            try:
                n = os.write(fd, view[:65536])
            except OSError as exc:
                raise PolicyFailure(f"policy closed its input: {exc}") from exc
            view = view[n:]

    def _recv(self) -> dict:
        fd = self.proc.stdout.fileno()
        t_start = time.monotonic()
        deadline = t_start + min(RESPONSE_TIMEOUT_S, max(SCENE_BUDGET_S - self.spent, 0.0))
        try:
            while b"\n" not in self.buf:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise PolicyFailure(f"no response within {RESPONSE_TIMEOUT_S} s or the "
                                        f"{SCENE_BUDGET_S} s per-scene budget is used up")
                readable, _, _ = select.select([fd], [], [], remaining)
                if not readable:
                    continue
                chunk = os.read(fd, 1 << 16)
                if not chunk:
                    raise PolicyFailure(f"policy exited (code {self.proc.poll()})")
                self.buf += chunk
                if len(self.buf) > MAX_RESPONSE_BYTES:
                    raise PolicyFailure("response exceeds size limit")
        finally:
            self.spent += time.monotonic() - t_start
        line, _, self.buf = self.buf.partition(b"\n")
        try:
            msg = json.loads(line)
        except (ValueError, RecursionError) as exc:
            raise PolicyFailure("response is not valid JSON") from exc
        if not isinstance(msg, dict):
            raise PolicyFailure("response must be a JSON object")
        return msg

    def frame_ops(self, frame: int, infos: list) -> list:
        self._send({"type": "frame", "frame": frame, "tiles": infos})
        msg = self._recv()
        ops = msg.get("ops")
        if not isinstance(ops, list) or len(ops) != NUM_TILES:
            raise PolicyFailure(f"response must contain 'ops' with one list per tile ({NUM_TILES})")
        return ops

    def stop(self) -> None:
        if self.proc is not None:
            try:
                self._send({"type": "end"})
            except Exception:
                pass
            try:
                self.proc.stdin.close()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
                try:
                    self.proc.wait(timeout=5)
                except Exception:
                    pass
            self.proc = None
        if self.log is not None:
            self.log.close()
            self.log = None


class BuiltinFullSort:
    """Exact per-frame re-sort of every tile on the same hardware model."""

    name = BASELINE_NAME

    def start(self, header: dict, scene_label: str) -> None:
        pass

    def frame_ops(self, frame: int, infos: list, members=None) -> list:
        return [full_sort_ops(len(m)) for m in members]

    def stop(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Lock-step scene runner
# ---------------------------------------------------------------------------
def _new_acc() -> dict:
    return {"traffic": 0, "no_deferred_extra": 0, "sq_err": 0.0, "n_vals": 0,
            "rank_err": 0, "n_rank": 0, "sum_L": 0, "sum_I": 0, "tile_frames": 0}


def _exact_frame(tiles: list) -> list:
    out = []
    for k, members in enumerate(tiles):
        order = sorted(members, key=lambda g: (members[g][0], g))
        rank = {g: i for i, g in enumerate(order)}
        pix = render_context(k, members)
        out.append((order, rank, pix, composite(pix, rank)))
    return out


def run_scene(scene_seed: int, speed: float, scene_label: str, runners: dict, failures: dict) -> dict:
    scene = generate_scene(scene_seed)
    header = {"tiles_x": TILES_X, "tiles_y": TILES_Y, "capacity": CAPACITY, "merge_fanin": MERGE_FANIN,
              "feedback_block": FEEDBACK_BLOCK, "max_ops_per_tile": MAX_OPS_PER_TILE}
    state = {}
    for name, runner in runners.items():
        if name in failures:
            continue
        try:
            runner.start(header, scene_label)
        except Exception as exc:
            failures[name] = f"{scene_label}: {exc}"
            runner.stop()
            continue
        state[name] = {"tables": None, "inv": None, "fit": None, "acc": _new_acc()}

    for frame in range(FRAMES):
        tiles = project_frame(scene, camera_pose(scene["traj"], frame, speed))
        if frame == 0:
            # Every method starts from the same exactly sorted tables.
            for st in state.values():
                st["tables"] = [[[g, m[g][0], True] for g in sorted(m, key=lambda g: (m[g][0], g))] for m in tiles]
                st["inv"] = [[0] * ((len(t) + FEEDBACK_BLOCK - 1) // FEEDBACK_BLOCK) for t in st["tables"]]
                st["fit"] = [[1.0, 0.0] for _ in range(NUM_TILES)]
            continue
        exact = _exact_frame(tiles)
        for name in list(state):
            if name in failures:
                continue
            st = state[name]
            runner = runners[name]
            try:
                incoming_all = []
                infos = []
                for k, members in enumerate(tiles):
                    table = st["tables"][k]
                    valid_ids = {e[0] for e in table if e[2]}
                    incoming = [g for g in members if g not in valid_ids]
                    incoming_all.append(incoming)
                    infos.append({"N": len(members), "L": len(table), "I": len(incoming), "X": len(table) - len(valid_ids),
                                  "inv": st["inv"][k],
                                  "depth_fit": [round(st["fit"][k][0], 9), round(st["fit"][k][1], 9)]})
                if isinstance(runner, BuiltinFullSort):
                    ops_all = runner.frame_ops(frame, infos, tiles)
                else:
                    ops_all = runner.frame_ops(frame, infos)
                acc = st["acc"]
                for k, members in enumerate(tiles):
                    tile_ops = ops_all[k]
                    regen = isinstance(tile_ops, list) and bool(tile_ops) and isinstance(tile_ops[0], dict) \
                        and tile_ops[0].get("op") == "regen"
                    acc["sum_L"] += infos[k]["L"]
                    acc["sum_I"] += infos[k]["I"]
                    table, traffic, inserted = execute_tile(st["tables"][k], members, incoming_all[k], tile_ops)
                    acc["traffic"] += traffic
                    if not regen:
                        acc["no_deferred_extra"] += 2 * len(table)
                    order, rank, pix, img_exact = exact[k]
                    rendered = [e[0] for e in table if e[0] in members]
                    if rendered == order:
                        acc["n_vals"] += 3 * len(img_exact)
                    else:
                        pos = {g: i for i, g in enumerate(rendered)}
                        img = composite(pix, pos)
                        sq = 0.0
                        for c1, c2 in zip(img, img_exact):
                            sq += (c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2
                        acc["sq_err"] += sq
                        acc["n_vals"] += 3 * len(img)
                        if len(pos) < len(members):
                            for g in order:
                                if g not in pos:
                                    pos[g] = len(pos)
                        acc["rank_err"] += sum(abs(pos[g] - r) for g, r in rank.items())
                    acc["n_rank"] += len(members)
                    acc["tile_frames"] += 1
                    inv, fit = deferred_update(table, members, inserted)
                    st["tables"][k] = table
                    st["inv"][k] = inv
                    st["fit"][k] = fit
            except (ProtocolError, PolicyFailure) as exc:
                failures[name] = f"{scene_label} frame {frame}: {exc}"
                runner.stop()
            except Exception as exc:  # anything a malformed response triggers fails that method only
                if isinstance(runner, BuiltinFullSort):
                    raise
                failures[name] = f"{scene_label} frame {frame}: {type(exc).__name__}: {exc}"
                runner.stop()
    for name in state:
        runners[name].stop()
    return {name: st["acc"] for name, st in state.items() if name not in failures}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def _clip(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


def psnr_drop_db(mse: float) -> float:
    """Drop of a reconstruction at the paper's mean original-3DGS PSNR when the
    ordering-induced error is added: 10*log10(1 + mse_order / mse_reconstruction)."""
    return 10.0 * math.log10(1.0 + mse / RECON_MSE)


def score_experiment(per_scene: dict, names: list, failures: dict) -> tuple[dict, dict]:
    base = per_scene[BASELINE_NAME]
    base_traffic = sum(acc["traffic"] for acc in base.values())
    results, diag = {}, {}
    for name in names:
        if name in failures or name not in per_scene:
            continue
        scenes = per_scene[name]
        traffic = sum(acc["traffic"] for acc in scenes.values())
        extra = sum(acc["no_deferred_extra"] for acc in scenes.values())
        drops = {s: psnr_drop_db(acc["sq_err"] / max(acc["n_vals"], 1)) for s, acc in scenes.items()}
        rank_err = sum(acc["rank_err"] for acc in scenes.values()) / max(sum(acc["n_rank"] for acc in scenes.values()), 1)
        values = {
            "traffic_reduction_pct": _clip(100.0 * (1.0 - traffic / base_traffic), *RANGES["traffic_reduction_pct"]),
            "psnr_drop_db": _clip(sum(drops.values()) / len(drops), *RANGES["psnr_drop_db"]),
            "mean_abs_rank_error": _clip(rank_err, *RANGES["mean_abs_rank_error"]),
        }
        if not all(math.isfinite(v) for v in values.values()):
            failures[name] = "non-finite metric"
            continue
        results[name] = values
        diag[name] = {
            "traffic_MB": traffic * ENTRY_BYTES / 1e6,
            "baseline_traffic_MB": base_traffic * ENTRY_BYTES / 1e6,
            "traffic_MB_without_deferred_depth_update": (traffic + extra) * ENTRY_BYTES / 1e6,
            "deferred_depth_update_savings_pct": 100.0 * extra / (traffic + extra) if traffic + extra else 0.0,
            "per_scene": {
                s: {
                    "traffic_reduction_pct": 100.0 * (1.0 - acc["traffic"] / base[s]["traffic"]),
                    "psnr_drop_db": drops[s],
                    "mean_abs_rank_error": acc["rank_err"] / max(acc["n_rank"], 1),
                    "mean_table_entries": acc["sum_L"] / max(acc["tile_frames"], 1),
                    "mean_incoming_entries": acc["sum_I"] / max(acc["tile_frames"], 1),
                }
                for s, acc in scenes.items()
            },
        }
    return results, diag


IGNORED_MANIFESTS: list = []


def discover_policies(policy_dir: Path) -> tuple[dict, dict]:
    commands, bad = {}, {}
    if not policy_dir.is_dir():
        return commands, bad
    for path in sorted(policy_dir.glob("*.json")):
        name = path.stem
        if name == BASELINE_NAME:
            # The baseline is fixed by the evaluator and cannot be replaced.
            IGNORED_MANIFESTS.append(str(path))
            continue
        if not name.replace("_", "a").replace("-", "a").isalnum():
            bad[name] = "invalid method name (use letters, digits, '_' or '-')"
            continue
        try:
            spec = json.loads(path.read_text())
            command = spec["command"]
            if not isinstance(command, list) or not command or not all(isinstance(c, str) for c in command):
                raise ValueError
        except Exception:
            bad[name] = "manifest must be a JSON object with a non-empty 'command' list of strings"
            continue
        commands[name] = command
    return commands, bad




def _scene_job(job: tuple) -> tuple:
    exp_name, idx, seed, speed, commands, log_dir = job
    label = f"{exp_name}.scene{idx}"
    runners: dict = {BASELINE_NAME: BuiltinFullSort()}
    for name, cmd in commands.items():
        runners[name] = SubprocessPolicy(name, cmd, Path(log_dir))
    failures: dict = {}
    accs = run_scene(seed, speed, label, runners, failures)
    return exp_name, label, accs, failures


def evaluate(policy_dir: Path, output: Path, diagnostics: Path, log_dir: Path, workers: int) -> dict:
    commands, failures = discover_policies(policy_dir)
    names = [BASELINE_NAME] + sorted(set(commands) | set(failures))
    jobs = [(exp_name, idx, seed, exp["speed"], commands, str(log_dir))
            for exp_name, exp in EXPERIMENTS.items() for idx, seed in enumerate(exp["scenes"])]
    workers = workers if workers > 0 else min(len(jobs), os.cpu_count() or 1)
    per_exp: dict = {exp_name: {} for exp_name in EXPERIMENTS}
    t0 = time.time()
    context = multiprocessing.get_context("fork")
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        for exp_name, label, accs, fails in pool.map(_scene_job, jobs):
            for name, acc in accs.items():
                per_exp[exp_name].setdefault(name, {})[label] = acc
            for name, reason in fails.items():
                failures.setdefault(name, reason)
            print(f"[{SPLIT}] {label} done ({time.time() - t0:.0f}s)", file=sys.stderr, flush=True)
    if BASELINE_NAME in failures:
        raise RuntimeError(f"built-in baseline failed: {failures[BASELINE_NAME]}")
    for exp_name, exp in EXPERIMENTS.items():
        for name in names:
            if name not in failures and len(per_exp[exp_name].get(name, {})) != len(exp["scenes"]):
                failures[name] = f"{exp_name}: did not complete every scene"
    scored, diag = {}, {}
    for exp_name, per_scene in per_exp.items():
        scored[exp_name], diag[exp_name] = score_experiment(per_scene, names, failures)
    # Rendering-quality constraint: a visibly degraded image fails the whole run.
    for exp_name, results in scored.items():
        for name, vals in results.items():
            if name not in failures and vals["psnr_drop_db"] > GATE_MAX_PSNR_DROP_DB[exp_name]:
                failures[name] = (f"{exp_name}: psnr_drop_db {vals['psnr_drop_db']:.4f} exceeds the "
                                  f"{GATE_MAX_PSNR_DROP_DB[exp_name]} dB rendering-quality constraint")
    experiments = {}
    for exp_name in EXPERIMENTS:
        results = {}
        for name in names:
            results[name] = dict(WORST[exp_name]) if name in failures else scored[exp_name][name]
        experiments[exp_name] = {"results": results}
    scores = {
        "_metadata": {
            "split": SPLIT,
            "failed_methods": {n: failures[n] for n in sorted(failures)},
            "ignored_manifests": list(IGNORED_MANIFESTS),
            "note": ("All numbers are computed by the evaluator, which generates the scenes, executes every "
                     "method's sorting operations on its own memory model and renders the result. Failed "
                     "methods receive the worst value of every scored metric in every experiment."),
        },
        "experiments": experiments,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scores, indent=2) + "\n")
    diagnostics.write_text(json.dumps({
        "_metadata": {"split": SPLIT, "failed_methods": scores["_metadata"]["failed_methods"],
                      "elapsed_s": round(time.time() - t0, 1)},
        "experiments": diag,
    }, indent=2) + "\n")
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--policy-dir", type=Path, default=REPO / "policies",
                        help="Directory of method manifests (<name>.json); every manifest is scored.")
    parser.add_argument("--output", type=Path, default=REPO / "scoring" / f"scores_{SPLIT}.json")
    parser.add_argument("--diagnostics", type=Path, default=None)
    parser.add_argument("--log-dir", type=Path, default=REPO / "outputs" / "eval_logs" / SPLIT)
    parser.add_argument("--workers", type=int, default=0, help="Scene-level worker processes (0 = auto).")
    args = parser.parse_args()
    diagnostics = args.diagnostics or args.output.with_name(args.output.stem.replace("scores", "diagnostics") + ".json")
    scores = evaluate(args.policy_dir, args.output, diagnostics, args.log_dir, args.workers)
    for exp_name, exp in scores["experiments"].items():
        for name, vals in exp["results"].items():
            print(f"{SPLIT} {exp_name:28s} {name:28s} " + " ".join(f"{k}={v:.4f}" for k, v in vals.items()))
    if scores["_metadata"]["failed_methods"]:
        print("failed:", json.dumps(scores["_metadata"]["failed_methods"], indent=1))


if __name__ == "__main__":
    main()
