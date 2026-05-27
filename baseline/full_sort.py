#!/usr/bin/env python3
"""Full per-frame sorting baseline for the Neo sorting benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ENTRY_BYTES = 8


def run(workload_path: Path, output_path: Path) -> None:
    workload = json.loads(workload_path.read_text())
    scenes = []
    for scene_name, scene in workload["scenes"].items():
        traffic_entries = 0
        entries = 0
        for frame in scene["frames"][1:]:
            for tile in frame:
                sorted(tile, key=lambda row: row["depth"])
                entries += len(tile)
                # Approximate multi-pass global sorting traffic in entries.
                traffic_entries += len(tile) * 10
        scenes.append(
            {
                "scene": scene_name,
                "frames_evaluated": max(0, len(scene["frames"]) - 1),
                "pair_order_accuracy": 1.0,
                "mean_abs_rank_error": 0.0,
                "p99_abs_rank_error": 0.0,
                "traffic_entries": traffic_entries,
                "traffic_MB": traffic_entries * ENTRY_BYTES / 1_000_000,
                "entries_sorted": entries,
            }
        )
    output = {"method": "full_sort", "workload": str(workload_path), "scenes": scenes}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", type=Path, default=Path("data/neo_synthetic_workload.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/full_sort.json"))
    args = parser.parse_args()
    run(args.workload, args.output)


if __name__ == "__main__":
    main()
