#!/usr/bin/env python3
"""Visible train-slice evaluator for the Neo sorting gym.

This evaluator reads method artifacts only. It does not import or execute
method code, so any future method can be scored by writing the same artifact
schema used by the original evaluator.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ENTRY_BYTES = 8
SLICE_NAME = "train"
FRAME_RULE = "frame_index_mod_4_in_1_or_2"


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    return json.loads(path.read_text())


def _include_frame(frame_idx: int) -> bool:
    return frame_idx % 4 in (1, 2)


def _method_name(path: Path) -> str:
    artifact = _load(path)
    return str(artifact.get("method") or path.stem)


def _is_ablation_artifact(method_name: str, artifact: dict) -> bool:
    return bool(artifact.get("separate_depth_refresh")) or "no_deferred" in method_name


def _artifact_map(outputs_dir: Path) -> dict[str, Path]:
    artifacts: dict[str, Path] = {}
    for path in sorted(outputs_dir.glob("*.json")):
        artifact = _load(path)
        if "scenes" not in artifact:
            continue
        method = str(artifact.get("method") or path.stem)
        if method in artifacts:
            raise ValueError(f"Duplicate artifact for method '{method}': {artifacts[method]} and {path}")
        artifacts[method] = path
    return artifacts


def _rank_error_metrics(predicted_ids: list[int], ideal_tile: list[dict]) -> dict:
    ideal_ids = [row["id"] for row in sorted(ideal_tile, key=lambda row: row["depth"])]
    ideal_rank = {row_id: idx for idx, row_id in enumerate(ideal_ids)}
    if sorted(predicted_ids) != sorted(ideal_ids):
        missing = set(ideal_ids) - set(predicted_ids)
        extra = set(predicted_ids) - set(ideal_ids)
        raise ValueError(f"Predicted order does not match tile membership: missing={len(missing)} extra={len(extra)}")
    if not predicted_ids:
        return {"mean_abs_rank_error": 0.0, "p99_abs_rank_error": 0.0, "pair_order_accuracy": 1.0}

    errors = sorted(abs(idx - ideal_rank[row_id]) for idx, row_id in enumerate(predicted_ids))
    mean_error = sum(errors) / len(errors)
    p99_error = errors[min(len(errors) - 1, int(0.99 * len(errors)))]

    correct_pairs = 0
    total_pairs = 0
    for stride in (32, 64, 128):
        if stride >= len(predicted_ids):
            continue
        for idx in range(0, len(predicted_ids) - stride, stride):
            total_pairs += 1
            if ideal_rank[predicted_ids[idx]] <= ideal_rank[predicted_ids[idx + stride]]:
                correct_pairs += 1
    return {
        "mean_abs_rank_error": mean_error,
        "p99_abs_rank_error": float(p99_error),
        "pair_order_accuracy": correct_pairs / total_pairs if total_pairs else 1.0,
    }


def _scene_metrics(scene_artifact: dict, scene_workload: dict) -> dict:
    workload_frames = scene_workload["frames"]
    total_entries = 0
    traffic_entries = 0
    weighted_pair_accuracy = 0.0
    weighted_mean_rank = 0.0
    weighted_p99_rank = 0.0
    frames = 0

    for frame_output in scene_artifact["frames"]:
        frame_idx = int(frame_output["frame"])
        if not _include_frame(frame_idx):
            continue
        frames += 1
        current_frame = workload_frames[frame_idx]
        for tile_output in frame_output["tiles"]:
            tile_idx = int(tile_output["tile"])
            current_tile = current_frame[tile_idx]
            metrics = _rank_error_metrics(tile_output["predicted_order"], current_tile)
            entries = len(current_tile)
            total_entries += entries
            traffic_entries += int(tile_output["traffic_entries"])
            weighted_pair_accuracy += metrics["pair_order_accuracy"] * entries
            weighted_mean_rank += metrics["mean_abs_rank_error"] * entries
            weighted_p99_rank += metrics["p99_abs_rank_error"] * entries

    denom = max(total_entries, 1)
    return {
        "pair_order_accuracy": weighted_pair_accuracy / denom,
        "mean_abs_rank_error": weighted_mean_rank / denom,
        "p99_abs_rank_error": weighted_p99_rank / denom,
        "traffic_entries": traffic_entries,
        "traffic_MB": traffic_entries * ENTRY_BYTES / 1_000_000,
        "frames": frames,
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
        "mean_abs_rank_error": sum(s["mean_abs_rank_error"] * s["entries"] for s in scene_metrics.values()) / total_entries,
        "p99_abs_rank_error": sum(s["p99_abs_rank_error"] * s["entries"] for s in scene_metrics.values()) / total_entries,
        "traffic_MB": sum(scene["traffic_MB"] for scene in scene_metrics.values()),
        "frames": total_frames,
    }


def _score_against_baseline(metrics: dict, baseline: dict, is_baseline: bool = False) -> dict:
    reduction = 0.0 if is_baseline else 100.0 * (1.0 - metrics["traffic_MB"] / baseline["traffic_MB"])
    return {
        "traffic_reduction_pct": reduction,
        "pair_order_accuracy": metrics["pair_order_accuracy"],
        "traffic_MB": metrics["traffic_MB"],
        "mean_abs_rank_error": metrics["mean_abs_rank_error"],
        "p99_abs_rank_error": metrics["p99_abs_rank_error"],
    }


def _matching_ablation_method(method_name: str, method_paths: dict[str, Path]) -> str | None:
    candidates = [
        method_name.replace("reuse_update", "no_deferred_depth_update"),
        f"{method_name}_no_deferred_depth_update",
        f"{method_name}_no_deferred",
    ]
    for candidate in candidates:
        if candidate != method_name and candidate in method_paths:
            return candidate
    return None


def _load_workload(artifact: dict) -> dict:
    workload_path = Path(artifact["workload"])
    return _load(workload_path)


def _select_method_paths(
    candidate: Path | None,
    baseline: Path | None,
    outputs_dir: Path,
) -> tuple[str, dict[str, Path]]:
    discovered = _artifact_map(outputs_dir)
    if baseline is not None:
        baseline_method = _method_name(baseline)
        discovered[baseline_method] = baseline
    elif "full_sort" in discovered:
        baseline_method = "full_sort"
    else:
        raise FileNotFoundError("Could not find a full_sort baseline artifact in outputs/")

    if candidate is not None:
        candidate_method = _method_name(candidate)
        discovered[candidate_method] = candidate
        selected = {baseline_method: discovered[baseline_method], candidate_method: candidate}
        ablation = _matching_ablation_method(candidate_method, discovered)
        if ablation is not None:
            selected[ablation] = discovered[ablation]
        return baseline_method, selected

    return baseline_method, discovered


def _evaluate_methods(method_paths: dict[str, Path], baseline_method: str) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    baseline_artifact = _load(method_paths[baseline_method])
    workload = _load_workload(baseline_artifact)
    baseline_metrics = _aggregate(_by_scene_metrics(baseline_artifact, workload))

    all_scores: dict[str, dict] = {}
    scene_scores: dict[str, dict] = {}
    method_metrics: dict[str, dict] = {}
    for method_name, path in sorted(method_paths.items()):
        artifact = _load(path)
        metrics_by_scene = _by_scene_metrics(artifact, workload)
        aggregate = _aggregate(metrics_by_scene)
        method_metrics[method_name] = aggregate
        all_scores[method_name] = _score_against_baseline(
            aggregate,
            baseline_metrics,
            is_baseline=(method_name == baseline_method),
        )
        for scene_name, scene_metric in metrics_by_scene.items():
            key = f"{method_name}_{scene_name}"
            scene_scores[key] = _score_against_baseline(
                scene_metric,
                _by_scene_metrics(baseline_artifact, workload)[scene_name],
                is_baseline=(method_name == baseline_method),
            )
    return all_scores, scene_scores, method_metrics


def evaluate(candidate: Path | None, baseline: Path | None, output: Path, outputs_dir: Path) -> None:
    baseline_method, method_paths = _select_method_paths(candidate, baseline, outputs_dir)
    primary_scores, scene_scores, method_metrics = _evaluate_methods(method_paths, baseline_method)

    synthetic_results = {
        method: scores
        for method, scores in primary_scores.items()
        if method == baseline_method or not _is_ablation_artifact(method, _load(method_paths[method]))
    }

    ablation_results: dict[str, dict] = {}
    for method, scores in primary_scores.items():
        result = dict(scores)
        artifact = _load(method_paths[method])
        if method == baseline_method or _is_ablation_artifact(method, artifact):
            result["deferred_update_savings_pct"] = 0.0
        else:
            ablation_method = _matching_ablation_method(method, method_paths)
            if ablation_method is None:
                result["deferred_update_savings_pct"] = 0.0
            else:
                ablation_traffic = method_metrics[ablation_method]["traffic_MB"]
                result["deferred_update_savings_pct"] = 100.0 * (1.0 - method_metrics[method]["traffic_MB"] / ablation_traffic)
        ablation_results[method] = result

    scores = {
        "_metadata": {
            "slice": SLICE_NAME,
            "frame_rule": FRAME_RULE,
            "description": "Visible train slice: frames with index modulo 4 equal to 1 or 2 in every scene.",
        },
        "experiments": {
            "synthetic_temporal_sorting": {
                "results": synthetic_results,
            },
            "deferred_depth_update_ablation": {
                "results": ablation_results,
            },
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scores, indent=2))

    diagnostics_path = output.with_name("per_regime_scores_train.json")
    diagnostics = {
        "_metadata": {"slice": SLICE_NAME, "frame_rule": FRAME_RULE},
        "experiments": {
            "synthetic_temporal_sorting_per_regime": {
                "results": scene_scores,
            }
        },
    }
    diagnostics_path.write_text(json.dumps(diagnostics, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=None, help="Optional candidate artifact path.")
    parser.add_argument("--baseline", type=Path, default=None, help="Optional baseline artifact path.")
    parser.add_argument("--output", type=Path, default=Path("scoring/scores_train.json"))
    parser.add_argument("--outputs-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    evaluate(args.candidate, args.baseline, args.output, args.outputs_dir)


if __name__ == "__main__":
    main()
