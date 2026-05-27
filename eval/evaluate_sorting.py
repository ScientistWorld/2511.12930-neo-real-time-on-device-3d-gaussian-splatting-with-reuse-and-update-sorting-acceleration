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


ENTRY_BYTES = 8


def _rank_error_metrics(predicted_ids: list[int], ideal_tile: list[dict]) -> dict:
    ideal_ids = [row["id"] for row in sorted(ideal_tile, key=lambda row: row["depth"])]
    ideal_rank = {row_id: idx for idx, row_id in enumerate(ideal_ids)}
    if sorted(predicted_ids) != sorted(ideal_ids):
        missing = set(ideal_ids) - set(predicted_ids)
        extra = set(predicted_ids) - set(ideal_ids)
        raise ValueError(f"Predicted order does not match tile membership: missing={len(missing)} extra={len(extra)}")
    if not predicted_ids:
        return {
            "mean_abs_rank_error": 0.0,
            "p99_abs_rank_error": 0.0,
            "pair_order_accuracy": 1.0,
            "adjacent_pair_accuracy": 1.0,
            "sampled_pair_order_accuracy": 1.0,
        }

    errors = sorted(abs(idx - ideal_rank[row_id]) for idx, row_id in enumerate(predicted_ids))
    mean_error = sum(errors) / len(errors)
    p99_error = errors[min(len(errors) - 1, int(0.99 * len(errors)))]

    correct_pairs = 0
    total_pairs = 0
    pair_step = max(len(predicted_ids) // 64, 1)
    for offset in (1, 2, 4, 8, 16, 32, 64, 128):
        if offset >= len(predicted_ids):
            continue
        for idx in range(0, len(predicted_ids) - offset, pair_step):
            total_pairs += 1
            if ideal_rank[predicted_ids[idx]] <= ideal_rank[predicted_ids[idx + offset]]:
                correct_pairs += 1
    adjacent_pairs = max(len(predicted_ids) - 1, 0)
    adjacent_correct = sum(
        1
        for idx in range(adjacent_pairs)
        if ideal_rank[predicted_ids[idx]] <= ideal_rank[predicted_ids[idx + 1]]
    )

    sampled_correct = 0
    sampled_total = 0
    sample_step = max(len(predicted_ids) // 64, 1)
    for offset in (3, 5, 9, 17, 33, 65, 129):
        if offset >= len(predicted_ids):
            continue
        start = min(offset // 2, len(predicted_ids) - offset - 1)
        for idx in range(start, len(predicted_ids) - offset, sample_step):
            sampled_total += 1
            if ideal_rank[predicted_ids[idx]] <= ideal_rank[predicted_ids[idx + offset]]:
                sampled_correct += 1
    return {
        "mean_abs_rank_error": mean_error,
        "p99_abs_rank_error": float(p99_error),
        "pair_order_accuracy": correct_pairs / total_pairs if total_pairs else 1.0,
        "adjacent_pair_accuracy": adjacent_correct / adjacent_pairs if adjacent_pairs else 1.0,
        "sampled_pair_order_accuracy": sampled_correct / sampled_total if sampled_total else 1.0,
    }


def _scene_metrics(scene_artifact: dict, scene_workload: dict) -> dict:
    workload_frames = scene_workload["frames"]
    total_entries = 0
    traffic_entries = 0
    weighted_pair_accuracy = 0.0
    weighted_adjacent_pair_accuracy = 0.0
    weighted_sampled_pair_accuracy = 0.0
    weighted_mean_rank = 0.0
    weighted_p99_rank = 0.0

    for frame_output in scene_artifact["frames"]:
        frame_idx = frame_output["frame"]
        current_frame = workload_frames[frame_idx]
        for tile_output in frame_output["tiles"]:
            tile_idx = tile_output["tile"]
            current_tile = current_frame[tile_idx]
            metrics = _rank_error_metrics(tile_output["predicted_order"], current_tile)
            entries = len(current_tile)
            total_entries += entries
            traffic_entries += int(tile_output["traffic_entries"])
            weighted_pair_accuracy += metrics["pair_order_accuracy"] * entries
            weighted_adjacent_pair_accuracy += metrics["adjacent_pair_accuracy"] * entries
            weighted_sampled_pair_accuracy += metrics["sampled_pair_order_accuracy"] * entries
            weighted_mean_rank += metrics["mean_abs_rank_error"] * entries
            weighted_p99_rank += metrics["p99_abs_rank_error"] * entries

    denom = max(total_entries, 1)
    return {
        "pair_order_accuracy": weighted_pair_accuracy / denom,
        "adjacent_pair_accuracy": weighted_adjacent_pair_accuracy / denom,
        "sampled_pair_order_accuracy": weighted_sampled_pair_accuracy / denom,
        "mean_abs_rank_error": weighted_mean_rank / denom,
        "p99_abs_rank_error": weighted_p99_rank / denom,
        "traffic_entries": traffic_entries,
        "traffic_MB": traffic_entries * ENTRY_BYTES / 1_000_000,
        "frames": len(scene_artifact["frames"]),
        "entries": total_entries,
    }


def _by_scene_metrics(artifact: dict, workload: dict) -> dict[str, dict]:
    workload_scenes = workload["scenes"]
    return {
        scene["scene"]: _scene_metrics(scene, workload_scenes[scene["scene"]])
        for scene in artifact["scenes"]
    }


def _aggregate(scene_metrics: dict[str, dict]) -> dict:
    total_frames = sum(scene["frames"] for scene in scene_metrics.values())
    total_entries = sum(scene["entries"] for scene in scene_metrics.values()) or 1
    return {
        "pair_order_accuracy": sum(s["pair_order_accuracy"] * s["entries"] for s in scene_metrics.values()) / total_entries,
        "adjacent_pair_accuracy": sum(s["adjacent_pair_accuracy"] * s["entries"] for s in scene_metrics.values()) / total_entries,
        "sampled_pair_order_accuracy": sum(s["sampled_pair_order_accuracy"] * s["entries"] for s in scene_metrics.values()) / total_entries,
        "mean_abs_rank_error": sum(s["mean_abs_rank_error"] * s["entries"] for s in scene_metrics.values()) / total_entries,
        "p99_abs_rank_error": sum(s["p99_abs_rank_error"] * s["entries"] for s in scene_metrics.values()) / total_entries,
        "traffic_MB": sum(scene["traffic_MB"] for scene in scene_metrics.values()),
        "frames": total_frames,
    }


def _scene_scores(neo_scenes: dict[str, dict], baseline_scenes: dict[str, dict]) -> dict:
    results = {}
    for scene_name in sorted(set(baseline_scenes) & set(neo_scenes)):
        baseline = baseline_scenes[scene_name]
        neo = neo_scenes[scene_name]
        reduction = 100.0 * (1.0 - neo["traffic_MB"] / baseline["traffic_MB"])
        results[f"full_sort_{scene_name}"] = {
            "traffic_reduction_pct": 0.0,
            "pair_order_accuracy": baseline["pair_order_accuracy"],
            "adjacent_pair_accuracy": baseline["adjacent_pair_accuracy"],
            "sampled_pair_order_accuracy": baseline["sampled_pair_order_accuracy"],
            "traffic_MB": baseline["traffic_MB"],
            "mean_abs_rank_error": baseline["mean_abs_rank_error"],
            "p99_abs_rank_error": baseline["p99_abs_rank_error"],
        }
        results[f"neo_reuse_update_{scene_name}"] = {
            "pair_order_accuracy": neo["pair_order_accuracy"],
            "adjacent_pair_accuracy": neo["adjacent_pair_accuracy"],
            "sampled_pair_order_accuracy": neo["sampled_pair_order_accuracy"],
            "traffic_MB": neo["traffic_MB"],
            "traffic_reduction_pct": reduction,
            "mean_abs_rank_error": neo["mean_abs_rank_error"],
            "p99_abs_rank_error": neo["p99_abs_rank_error"],
        }
    return results


def evaluate(neo_path: Path, baseline_path: Path, output_path: Path) -> None:
    neo_artifact = _load(neo_path)
    baseline_artifact = _load(baseline_path)
    workload_path = Path(neo_artifact["workload"])
    workload = _load(workload_path)
    neo_scenes = _by_scene_metrics(neo_artifact, workload)
    baseline_scenes = _by_scene_metrics(baseline_artifact, workload)
    neo = _aggregate(neo_scenes)
    baseline = _aggregate(baseline_scenes)
    reduction = 100.0 * (1.0 - neo["traffic_MB"] / baseline["traffic_MB"])

    experiment_results = {
        "full_sort": {
            "traffic_reduction_pct": 0.0,
            "pair_order_accuracy": baseline["pair_order_accuracy"],
            "adjacent_pair_accuracy": baseline["adjacent_pair_accuracy"],
            "sampled_pair_order_accuracy": baseline["sampled_pair_order_accuracy"],
            "traffic_MB": baseline["traffic_MB"],
            "mean_abs_rank_error": baseline["mean_abs_rank_error"],
            "p99_abs_rank_error": baseline["p99_abs_rank_error"],
        },
        "neo_reuse_update": {
            "pair_order_accuracy": neo["pair_order_accuracy"],
            "adjacent_pair_accuracy": neo["adjacent_pair_accuracy"],
            "sampled_pair_order_accuracy": neo["sampled_pair_order_accuracy"],
            "traffic_MB": neo["traffic_MB"],
            "traffic_reduction_pct": reduction,
            "mean_abs_rank_error": neo["mean_abs_rank_error"],
            "p99_abs_rank_error": neo["p99_abs_rank_error"],
        },
    }
    scores = {
        "experiments": {
            "synthetic_temporal_sorting": {
                "results": experiment_results
            }
        }
    }
    no_deferred_path = neo_path.with_name("neo_no_deferred_depth_update.json")
    if no_deferred_path.exists():
        no_deferred_artifact = _load(no_deferred_path)
        no_deferred_scenes = _by_scene_metrics(no_deferred_artifact, workload)
        no_deferred = _aggregate(no_deferred_scenes)
        no_deferred_reduction = 100.0 * (1.0 - no_deferred["traffic_MB"] / baseline["traffic_MB"])
        deferred_savings = 100.0 * (1.0 - neo["traffic_MB"] / no_deferred["traffic_MB"])
        scores["experiments"]["deferred_depth_update_ablation"] = {
            "results": {
                "full_sort": {
                    **experiment_results["full_sort"],
                    "deferred_update_savings_pct": 0.0,
                    "deferred_update_savings_MB": 0.0,
                },
                "neo_no_deferred_depth_update": {
                    "pair_order_accuracy": no_deferred["pair_order_accuracy"],
                    "adjacent_pair_accuracy": no_deferred["adjacent_pair_accuracy"],
                    "sampled_pair_order_accuracy": no_deferred["sampled_pair_order_accuracy"],
                    "traffic_MB": no_deferred["traffic_MB"],
                    "traffic_reduction_pct": no_deferred_reduction,
                    "deferred_update_savings_pct": 0.0,
                    "deferred_update_savings_MB": 0.0,
                    "mean_abs_rank_error": no_deferred["mean_abs_rank_error"],
                    "p99_abs_rank_error": no_deferred["p99_abs_rank_error"],
                },
                "neo_reuse_update": {
                    **experiment_results["neo_reuse_update"],
                    "deferred_update_savings_pct": deferred_savings,
                    "deferred_update_savings_MB": no_deferred["traffic_MB"] - neo["traffic_MB"],
                },
            }
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(scores, indent=2))
    diagnostics_path = output_path.with_name("per_regime_scores.json")
    diagnostics = {
        "experiments": {
            "synthetic_temporal_sorting_per_regime": {
                "results": _scene_scores(neo_scenes, baseline_scenes)
            }
        }
    }
    diagnostics_path.write_text(json.dumps(diagnostics, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--neo", type=Path, default=Path("outputs/neo_reuse_update.json"))
    parser.add_argument("--baseline", type=Path, default=Path("outputs/full_sort.json"))
    parser.add_argument("--output", type=Path, default=Path("scoring/scores.json"))
    args = parser.parse_args()
    evaluate(args.neo, args.baseline, args.output)


if __name__ == "__main__":
    main()
