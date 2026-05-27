# Overview

- **Paper ID:** 2511.12930
- **Title:** Neo: Real-Time On-Device 3D Gaussian Splatting with Reuse-and-Update Sorting Acceleration
- **Domain:** Computer Architecture / Neural Rendering Acceleration
- **TL;DR:** Neo accelerates on-device 3D Gaussian Splatting by reusing and incrementally updating per-tile Gaussian depth order across frames.

## Short Summary

The paper identifies sorting as the dominant memory-bandwidth bottleneck for high-resolution 3DGS rendering on edge devices. Neo exploits temporal similarity across consecutive camera poses by updating prior sorted Gaussian tables instead of fully sorting every frame. The paper couples this algorithm with a specialized sorting/rasterization accelerator and reports large throughput and DRAM-traffic improvements with negligible image-quality loss.

## Key Results

- QHD DRAM traffic for 60 frames drops from 104.6 GB on GSCore to 19.6 GB on Neo.
- Neo reports 99.3 FPS average QHD throughput and 5.6x speedup over GSCore.
- Rendering quality changes by at most 0.1 dB PSNR and 0.001 LPIPS across six scenes.

---

# Problem Definition

## Research Question

How can an on-device 3D Gaussian Splatting renderer maintain correct per-tile depth ordering across a sequence of camera poses while greatly reducing the memory traffic normally caused by sorting every tile from scratch for every frame?

## Why It Matters

High-resolution AR/VR rendering needs low latency and high frame rate on memory-constrained devices. In 3DGS, depth sorting can dominate off-chip traffic, so reducing sorting traffic without corrupting visual order is necessary for practical on-device rendering.

## Success Criteria

A successful solution should process temporally adjacent per-tile Gaussian tables, reduce sorting-related traffic relative to full per-frame sorting, and preserve near-correct depth order so rendering quality is not meaningfully degraded.

---

# Paper's Method

## Key Contribution

Neo introduces reuse-and-update sorting for 3D Gaussian Splatting and pairs it with hardware support for low-traffic on-device rendering. The core software-visible contribution is to carry forward each tile's sorted Gaussian table from the previous frame and update it incrementally instead of globally sorting from scratch.

## Approach

For each frame and tile, Neo performs four operations. First, it reorders the previous Gaussian table with Dynamic Partial Sorting: entries are sorted in chunks of up to 256 Gaussians, and chunk boundaries alternate by half a chunk across frames so entries can migrate across prior boundaries. Second, newly visible Gaussians are sorted and inserted. Third, outgoing Gaussians are deleted during the merge. Fourth, depth values are refreshed during rasterization so the next frame can reuse the updated table without an extra random depth-fetch pass.

The hardware design contains preprocessing, sorting, and rasterization engines. The sorting engine includes bitonic sorting and merge units for chunk sorting, insertion, and deletion; the rasterization engine supports subtile rasterization and on-the-fly depth/valid-bit update.

## Main Claims

The primary claim is that temporal reuse of sorted Gaussian tables greatly reduces sorting-induced memory traffic while preserving rendering quality. The paper reports 81.3% lower QHD DRAM traffic than GSCore and 94.4% lower than Orin AGX for 60 frames, with less than 0.1 dB PSNR and 0.001 LPIPS degradation.

Secondary claims include higher end-to-end throughput than Orin AGX and GSCore, robustness to larger scenes and rapid camera movement, and small hardware area/power overhead.

---

# Evaluation

## Metrics

The benchmark measures memory traffic and ordering quality over a deterministic temporal sequence of per-tile Gaussian tables.

`traffic_MB` estimates table-entry memory traffic; lower is better. `traffic_reduction_pct` compares a candidate against full per-frame sorting; higher is better. `pair_order_accuracy` checks deterministic broad pair relationships in each output order against exact depth-sorted order; higher is better. `mean_abs_rank_error` and `p99_abs_rank_error` measure displacement from exact depth rank; lower is better.

## Baselines and Targets

The baseline is full sorting of each tile at each frame, which has perfect ordering but high memory traffic. The paper reports QHD traffic for 60 frames of 104.6 GB for GSCore and 19.6 GB for Neo, an 81.3% reduction, while quality degradation remains under 0.1 dB PSNR and 0.001 LPIPS. This reproduction uses an ordering-quality proxy instead of image PSNR because trained 3DGS scene checkpoints are not released.

## Evaluation Protocol

Run `bash scripts/reproduce.sh` to generate the deterministic workload, run the full-sort baseline, run the candidate method, run the no-deferred-depth ablation, and write `scoring/scores.json`. Evaluation code in `eval/` reads per-tile predicted-order artifacts under `outputs/`, recomputes ordering quality against the workload, and must not import candidate method code. Workload generation uses a fixed seed and three temporal settings: high-retention, moderate-retention, and rapid-motion.

---

# Reproduction Log

### Iteration 1: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 8m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-27 02:20] - none
- Started reproduction of Neo from paper markdown.
- Identified the core reproducible algorithm: reuse-and-update sorting for per-tile 3DGS Gaussian tables.

### [2026-05-27 02:55] - method_runs
- Implemented Dynamic Partial Sorting with alternating half-chunk boundaries, insertion, deletion, and deferred depth refresh in `method/neo_sort.py`.
- Implemented full per-frame sorting baseline and method-agnostic evaluator.
- Local CPU reproduction runs end-to-end and writes `scoring/scores.json`.

### [2026-05-27 03:05] - core_claim
- Scheduler CPU test job `a5d0ec7a-e50` completed with exit code 0.
- Container run reproduced the benchmark and `python validate.py --compare` passed.
- Reuse-and-update sorting reduced table traffic by 54.62% versus full sorting while preserving broad pair order and keeping p99 rank error at 6.28 positions.

</details>

### Iteration 2: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 6m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-27 02:05] - core_claim
- Implemented Neo's reuse-and-update sorting algorithm: Dynamic Partial Sorting with interleaved chunk boundaries, insertion, deletion, and deferred depth update.
- Implemented exact full per-frame sorting baseline and artifact-only evaluator.
- Reproduced the central benefit/constraint tradeoff on deterministic temporal Gaussian-table traces: 54.62% sorting-traffic reduction with pair-order accuracy 1.0.
- `bash scripts/reproduce.sh` and `python validate.py --compare` pass locally; submitting a CPU test job to verify the packaged path in the compute container.

### [2026-05-27 02:09] - core_claim_plus
- Fixed evaluation integrity so `eval/` recomputes ordering quality from per-frame, per-tile predicted orders instead of trusting method-reported metrics.
- Fixed traffic accounting to compare Neo and full sorting over the same post-seed temporal update interval.
- Added `scoring/per_regime_scores.json` diagnostics for high-retention, moderate-retention, and rapid-motion synthetic settings.
- Local results show traffic reductions of 57.60%, 56.39%, and 54.01% across the three regimes while preserving pair-order accuracy 1.0.

### [2026-05-27 02:10] - core_claim_plus
- Scheduler CPU test job `597e7566-ff8` completed with exit code 0.
- The compute-container run reproduced the independent-evaluator result: 55.955% aggregate traffic reduction, pair-order accuracy 1.0, mean rank error 1.686, and p99 rank error 6.350.
- Stopping at `core_claim_plus` because higher milestones require unreleased trained 3DGS scene artifacts, the authors' cycle simulator, or RTL-level hardware details.

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 10m | **GPU**: 0.0h
- **Jobs**: 3 total (3 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-27 02:11] - method_runs
- Implemented Neo's reuse-and-update sorting flow: Dynamic Partial Sorting with interleaved chunk boundaries, insertion, deletion, and deferred depth update.
- Implemented the full per-frame sorting baseline and artifact-based evaluator.
- Verified `bash scripts/reproduce.sh` and `python validate.py --compare` locally.

### [2026-05-27 02:11] - core_claim
- Demonstrated the central benefit/constraint tradeoff on a deterministic temporal 3DGS sorting workload.
- Reproduced a traffic reduction versus full sorting while preserving near-correct ordering: Neo achieved 55.95% lower table traffic with pair-order accuracy 1.0.
- Verified the same workflow inside the scheduler container with CPU test job `597e7566-ff8`.

### [2026-05-27 02:13] - core_claim_plus
- Added per-regime diagnostics for high-retention, moderate-retention, and rapid-motion temporal traces.
- Each regime shows substantial traffic reduction while maintaining pair-order accuracy, giving future agents multiple settings to improve.

### [2026-05-27 02:20] - core_claim_plus
- Audited the continuation workspace and confirmed the method implementation contains Neo's paper-specific reuse-and-update sorting steps rather than a surrogate model.
- Added and locally validated a deferred-depth-update ablation: no-deferred Neo uses 21.2486 MB, while full Neo uses 14.6131 MB, showing a 31.2280% traffic saving from the deferred update path on the scaled workload.
- Kept the milestone at `core_claim_plus`; higher milestones still require unreleased trained 3DGS scene checkpoints, the authors' cycle simulator or RTL, and full image rendering/quality evaluation.

### [2026-05-27 02:23] - core_claim_plus
- Scheduler CPU test job `aff60dc0-5e4` completed successfully inside the packaged container.
- The job reran `bash scripts/run.sh` and passed `python validate.py --compare` with both `synthetic_temporal_sorting` and `deferred_depth_update_ablation` present in `scoring/scores.json`.

</details>

### Iteration 4: gpt-5.5 (designer_stage_1)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 6m | **GPU**: 0.0h
- **Jobs**: 3 total (3 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-27 02:11] - method_runs
- Implemented Neo's reuse-and-update sorting flow: Dynamic Partial Sorting with interleaved chunk boundaries, insertion, deletion, and deferred depth update.
- Implemented the full per-frame sorting baseline and artifact-based evaluator.
- Verified `bash scripts/reproduce.sh` and `python validate.py --compare` locally.

### [2026-05-27 02:11] - core_claim
- Demonstrated the central benefit/constraint tradeoff on a deterministic temporal 3DGS sorting workload.
- Reproduced a traffic reduction versus full sorting while preserving near-correct ordering: Neo achieved 55.95% lower table traffic with pair-order accuracy 1.0.
- Verified the same workflow inside the scheduler container with CPU test job `597e7566-ff8`.

### [2026-05-27 02:13] - core_claim_plus
- Added per-regime diagnostics for high-retention, moderate-retention, and rapid-motion temporal traces.
- Each regime shows substantial traffic reduction while maintaining pair-order accuracy, giving future agents multiple settings to improve.

### [2026-05-27 02:20] - core_claim_plus
- Audited the continuation workspace and confirmed the method implementation contains Neo's paper-specific reuse-and-update sorting steps rather than a surrogate model.
- Added and locally validated a deferred-depth-update ablation: no-deferred Neo uses 21.2486 MB, while full Neo uses 14.6131 MB, showing a 31.2280% traffic saving from the deferred update path on the scaled workload.
- Kept the milestone at `core_claim_plus`; higher milestones still require unreleased trained 3DGS scene checkpoints, the authors' cycle simulator or RTL, and full image rendering/quality evaluation.

### [2026-05-27 02:23] - core_claim_plus
- Scheduler CPU test job `aff60dc0-5e4` completed successfully inside the packaged container.
- The job reran `bash scripts/run.sh` and passed `python validate.py --compare` with both `synthetic_temporal_sorting` and `deferred_depth_update_ablation` present in `scoring/scores.json`.

</details>

### Iteration 5: gpt-5.5 (designer_stage_2)
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 3m | **GPU**: 0.0h
- **Jobs**: 3 total (3 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-27 02:11] - method_runs
- Implemented Neo's reuse-and-update sorting flow: Dynamic Partial Sorting with interleaved chunk boundaries, insertion, deletion, and deferred depth update.
- Implemented the full per-frame sorting baseline and artifact-based evaluator.
- Verified `bash scripts/reproduce.sh` and `python validate.py --compare` locally.

### [2026-05-27 02:11] - core_claim
- Demonstrated the central benefit/constraint tradeoff on a deterministic temporal 3DGS sorting workload.
- Reproduced a traffic reduction versus full sorting while preserving near-correct ordering: Neo achieved 55.95% lower table traffic with pair-order accuracy 1.0.
- Verified the same workflow inside the scheduler container with CPU test job `597e7566-ff8`.

### [2026-05-27 02:13] - core_claim_plus
- Added per-regime diagnostics for high-retention, moderate-retention, and rapid-motion temporal traces.
- Each regime shows substantial traffic reduction while maintaining pair-order accuracy, giving future agents multiple settings to improve.

### [2026-05-27 02:20] - core_claim_plus
- Audited the continuation workspace and confirmed the method implementation contains Neo's paper-specific reuse-and-update sorting steps rather than a surrogate model.
- Added and locally validated a deferred-depth-update ablation: no-deferred Neo uses 21.2486 MB, while full Neo uses 14.6131 MB, showing a 31.2280% traffic saving from the deferred update path on the scaled workload.
- Kept the milestone at `core_claim_plus`; higher milestones still require unreleased trained 3DGS scene checkpoints, the authors' cycle simulator or RTL, and full image rendering/quality evaluation.

### [2026-05-27 02:23] - core_claim_plus
- Scheduler CPU test job `aff60dc0-5e4` completed successfully inside the packaged container.
- The job reran `bash scripts/run.sh` and passed `python validate.py --compare` with both `synthetic_temporal_sorting` and `deferred_depth_update_ablation` present in `scoring/scores.json`.

</details>


---

# Reproduction Milestones

**Current: core_claim_plus**

## Stop Justification
- Completed at milestone `core_claim_plus`.
