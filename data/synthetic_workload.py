#!/usr/bin/env python3
"""Synthetic 3DGS sorting workloads for Neo reproduction.

The original paper evaluates trained 3D Gaussian scenes from Tanks and Temples.
Those trained Gaussian checkpoints and the authors' cycle simulator are not
released with the paper. This module creates deterministic per-tile Gaussian
visibility/depth traces that preserve the sorting problem Neo targets: high
retention across consecutive frames, small rank drift for most reused Gaussians,
and a small stream of incoming/outgoing Gaussians.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path


SCENES = {
    "family_like": {"tiles": 16, "gaussians_per_tile": 512, "retention": 0.92, "drift": 0.0018},
    "train_like": {"tiles": 16, "gaussians_per_tile": 640, "retention": 0.88, "drift": 0.0024},
    "rapid_motion": {"tiles": 16, "gaussians_per_tile": 576, "retention": 0.80, "drift": 0.0042},
}


def _initial_tile(rng: random.Random, count: int, id_start: int) -> tuple[list[dict], int]:
    rows = []
    for offset in range(count):
        # Keep depths well separated initially, then let camera motion perturb them.
        base = offset / max(count - 1, 1)
        rows.append({"id": id_start + offset, "depth": base + rng.uniform(-1e-4, 1e-4)})
    rows.sort(key=lambda row: row["depth"])
    return rows, id_start + count


def generate_workload(
    output: Path,
    frames: int = 16,
    chunk_size: int = 256,
    seed: int = 251112930,
) -> None:
    rng = random.Random(seed)
    output.parent.mkdir(parents=True, exist_ok=True)

    workload = {
        "metadata": {
            "description": "Deterministic synthetic per-tile Gaussian depth traces for Neo sorting.",
            "frames": frames,
            "chunk_size": chunk_size,
            "seed": seed,
        },
        "scenes": {},
    }

    next_id = 0
    for scene_name, cfg in SCENES.items():
        scene_frames: list[list[list[dict]]] = []
        current_tiles: list[list[dict]] = []
        for _tile in range(cfg["tiles"]):
            tile_rows, next_id = _initial_tile(rng, cfg["gaussians_per_tile"], next_id)
            current_tiles.append(tile_rows)

        for frame_idx in range(frames):
            if frame_idx == 0:
                scene_frames.append([[dict(row) for row in tile] for tile in current_tiles])
                continue

            next_tiles = []
            for tile in current_tiles:
                keep_count = max(1, int(round(len(tile) * cfg["retention"])))
                kept = rng.sample(tile, keep_count)
                incoming_count = len(tile) - keep_count
                moved_rows = []
                camera_wave = math.sin(frame_idx * 0.37) * cfg["drift"] * 2.5
                for row in kept:
                    # Smooth depth drift plus small independent noise models adjacent camera poses.
                    moved_rows.append(
                        {
                            "id": row["id"],
                            "depth": row["depth"]
                            + camera_wave
                            + rng.gauss(0.0, cfg["drift"]),
                        }
                    )
                for _ in range(incoming_count):
                    moved_rows.append({"id": next_id, "depth": rng.random()})
                    next_id += 1
                moved_rows.sort(key=lambda row: row["depth"])
                next_tiles.append(moved_rows)
            current_tiles = next_tiles
            scene_frames.append([[dict(row) for row in tile] for tile in current_tiles])

        workload["scenes"][scene_name] = {
            "config": cfg,
            "frames": scene_frames,
        }

    output.write_text(json.dumps(workload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/neo_synthetic_workload.json"))
    parser.add_argument("--frames", type=int, default=16)
    parser.add_argument("--chunk-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=251112930)
    args = parser.parse_args()
    generate_workload(args.output, args.frames, args.chunk_size, args.seed)


if __name__ == "__main__":
    main()
