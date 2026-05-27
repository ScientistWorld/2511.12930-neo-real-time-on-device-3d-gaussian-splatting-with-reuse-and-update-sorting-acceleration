#!/usr/bin/env python3
"""Evaluate sorting artifacts for the Neo reproduction gym.

This module reads method outputs only. It does not import or execute code from
method/, so future methods can be evaluated by writing the same artifact schema.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    return json.loads(path.read_text())


def _aggregate(artifact: dict) -> dict:
    scenes = artifact["scenes"]
    frames = sum(scene["frames_evaluated"] for scene in scenes)
    traffic = sum(scene["traffic_MB"] for scene in scenes)
    weights = [max(scene.get("frames_evaluated", 1), 1) for scene in scenes]
    total_weight = sum(weights) or 1
    return {
        "pair_order_accuracy": sum(s["pair_order_accuracy"] * w for s, w in zip(scenes, weights)) / total_weight,
        "mean_abs_rank_error": sum(s["mean_abs_rank_error"] * w for s, w in zip(scenes, weights)) / total_weight,
        "p99_abs_rank_error": sum(s["p99_abs_rank_error"] * w for s, w in zip(scenes, weights)) / total_weight,
        "traffic_MB": traffic,
        "frames": frames,
    }


def evaluate(neo_path: Path, baseline_path: Path, output_path: Path) -> None:
    neo = _aggregate(_load(neo_path))
    baseline = _aggregate(_load(baseline_path))
    reduction = 100.0 * (1.0 - neo["traffic_MB"] / baseline["traffic_MB"])

    scores = {
        "experiments": {
            "synthetic_temporal_sorting": {
                "results": {
                    "full_sort": {
                        "traffic_reduction_pct": 0.0,
                        "pair_order_accuracy": baseline["pair_order_accuracy"],
                        "traffic_MB": baseline["traffic_MB"],
                        "mean_abs_rank_error": baseline["mean_abs_rank_error"],
                        "p99_abs_rank_error": baseline["p99_abs_rank_error"],
                    },
                    "neo_reuse_update": {
                        "pair_order_accuracy": neo["pair_order_accuracy"],
                        "traffic_MB": neo["traffic_MB"],
                        "traffic_reduction_pct": reduction,
                        "mean_abs_rank_error": neo["mean_abs_rank_error"],
                        "p99_abs_rank_error": neo["p99_abs_rank_error"],
                    },
                }
            }
        }
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(scores, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--neo", type=Path, default=Path("outputs/neo_reuse_update.json"))
    parser.add_argument("--baseline", type=Path, default=Path("outputs/full_sort.json"))
    parser.add_argument("--output", type=Path, default=Path("scoring/scores.json"))
    args = parser.parse_args()
    evaluate(args.neo, args.baseline, args.output)


if __name__ == "__main__":
    main()
