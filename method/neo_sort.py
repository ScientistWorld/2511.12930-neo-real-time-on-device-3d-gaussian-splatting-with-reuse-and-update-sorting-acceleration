#!/usr/bin/env python3
"""Neo reuse-and-update sorting simulator.

This implements the paper's software-visible algorithmic steps:
dynamic partial sorting with interleaved chunk boundaries, insertion,
deletion of outgoing Gaussians, and deferred depth update.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ENTRY_BYTES = 8  # 32-bit Gaussian id + 32-bit depth, used for traffic accounting.


def dynamic_partial_sort(table: list[dict], frame_idx: int, chunk_size: int) -> tuple[list[dict], int]:
    """Sort one pass of interleaved chunks from the previous Gaussian table."""
    if not table:
        return [], 0
    start = 0 if frame_idx % 2 == 1 else chunk_size // 2
    result = [dict(row) for row in table]
    accessed = 0

    if start > 0:
        prefix = result[:start]
        prefix.sort(key=lambda row: row["depth"])
        result[:start] = prefix
        accessed += len(prefix)

    pos = start
    while pos < len(result):
        end = min(pos + chunk_size, len(result))
        chunk = result[pos:end]
        chunk.sort(key=lambda row: row["depth"])
        result[pos:end] = chunk
        accessed += len(chunk)
        pos += chunk_size
    return result, accessed


def merge_insert_delete(reused: list[dict], current: list[dict], incoming: list[dict]) -> tuple[list[dict], int]:
    current_ids = {row["id"] for row in current}
    incoming_sorted = sorted((dict(row) for row in incoming), key=lambda row: row["depth"])
    valid_reused = [row for row in reused if row["id"] in current_ids]

    merged = []
    i = 0
    j = 0
    while i < len(valid_reused) and j < len(incoming_sorted):
        if valid_reused[i]["depth"] <= incoming_sorted[j]["depth"]:
            merged.append(valid_reused[i])
            i += 1
        else:
            merged.append(incoming_sorted[j])
            j += 1
    merged.extend(valid_reused[i:])
    merged.extend(incoming_sorted[j:])
    merge_accesses = len(reused) + len(incoming_sorted) + len(merged)
    return merged, merge_accesses


def update_depths_after_rasterization(table: list[dict], current: list[dict]) -> list[dict]:
    current_depth = {row["id"]: row["depth"] for row in current}
    return [{"id": row["id"], "depth": current_depth[row["id"]]} for row in table if row["id"] in current_depth]


def rank_error_metrics(predicted: list[dict], ideal: list[dict]) -> dict:
    ideal_rank = {row["id"]: idx for idx, row in enumerate(ideal)}
    pred_ids = [row["id"] for row in predicted]
    if not pred_ids:
        return {"mean_abs_rank_error": 0.0, "p99_abs_rank_error": 0.0, "pair_order_accuracy": 1.0}

    errors = sorted(abs(idx - ideal_rank[row_id]) for idx, row_id in enumerate(pred_ids))
    mean_error = sum(errors) / len(errors)
    p99_error = errors[min(len(errors) - 1, int(0.99 * len(errors)))]

    # Sample deterministic pair distances across the tile. This captures broad
    # depth-order preservation without requiring exact adjacent rank equality.
    correct_pairs = 0
    total_pairs = 0
    strides = (32, 64, 128)
    for stride in strides:
        if stride >= len(pred_ids):
            continue
        for idx in range(0, len(pred_ids) - stride, stride):
            left = pred_ids[idx]
            right = pred_ids[idx + stride]
            total_pairs += 1
            if ideal_rank[left] <= ideal_rank[right]:
                correct_pairs += 1
    pair_acc = correct_pairs / total_pairs if total_pairs else 1.0
    return {
        "mean_abs_rank_error": mean_error,
        "p99_abs_rank_error": float(p99_error),
        "pair_order_accuracy": pair_acc,
    }


def run_scene(
    scene_name: str,
    frames: list,
    chunk_size: int,
    separate_depth_refresh: bool = False,
) -> dict:
    previous_table: list[list[dict]] | None = None
    frame_outputs = []
    neo_accesses = 0

    for frame_idx, tiles in enumerate(frames):
        if frame_idx == 0:
            # Seed the reusable table with exact sorted order. Traffic accounting
            # starts from frame 1 so Neo and full-sort baseline compare the same
            # temporal update interval.
            previous_table = [sorted((dict(row) for row in tile), key=lambda row: row["depth"]) for tile in tiles]
            continue

        assert previous_table is not None
        new_previous = []
        tile_outputs = []
        for tile_idx, current_tile in enumerate(tiles):
            prev_tile = previous_table[tile_idx]
            prev_ids = {row["id"] for row in prev_tile}
            incoming = [row for row in current_tile if row["id"] not in prev_ids]
            reordered, partial_accesses = dynamic_partial_sort(prev_tile, frame_idx, chunk_size)
            merged, merge_accesses = merge_insert_delete(reordered, current_tile, incoming)
            tile_accesses = 2 * partial_accesses + merge_accesses + 2 * len(incoming)
            if separate_depth_refresh:
                # Ablation for removing Neo's deferred depth update: after
                # rasterization the table must be refreshed by a separate read
                # of current depths and a writeback of table entries.
                tile_accesses += 2 * len(merged)
            neo_accesses += tile_accesses
            tile_outputs.append(
                {
                    "tile": tile_idx,
                    "predicted_order": [row["id"] for row in merged],
                    "traffic_entries": tile_accesses,
                }
            )
            new_previous.append(update_depths_after_rasterization(merged, current_tile))
        previous_table = new_previous
        frame_outputs.append({"frame": frame_idx, "tiles": tile_outputs})

    return {
        "scene": scene_name,
        "frames_evaluated": len(frame_outputs),
        "traffic_entries": neo_accesses,
        "traffic_MB": neo_accesses * ENTRY_BYTES / 1_000_000,
        "frames": frame_outputs,
    }


def run(workload_path: Path, output_path: Path, separate_depth_refresh: bool = False) -> None:
    workload = json.loads(workload_path.read_text())
    chunk_size = int(workload["metadata"]["chunk_size"])
    scenes = []
    for scene_name, scene in workload["scenes"].items():
        scenes.append(run_scene(scene_name, scene["frames"], chunk_size, separate_depth_refresh))
    output = {
        "method": "neo_no_deferred_depth_update" if separate_depth_refresh else "neo_reuse_update",
        "workload": str(workload_path),
        "chunk_size": chunk_size,
        "separate_depth_refresh": separate_depth_refresh,
        "scenes": scenes,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", type=Path, default=Path("data/neo_synthetic_workload.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/neo_reuse_update.json"))
    parser.add_argument(
        "--separate-depth-refresh",
        action="store_true",
        help="Ablate Neo's deferred depth update by charging a separate depth-refresh pass.",
    )
    args = parser.parse_args()
    run(args.workload, args.output, args.separate_depth_refresh)


if __name__ == "__main__":
    main()
