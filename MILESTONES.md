# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

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

### [2026-05-27 02:53] - core_claim_plus
- Replaced the earlier deletion oracle with a valid-bit flow: rasterization-like visibility marks outgoing Gaussians, and the next merge step removes invalid entries.
- Extended `scoring/scores.json` with adjacent-pair, sampled-pair, and deferred-update MB metrics, then locally reran reproduction, train/test evaluation, and validation successfully.
- Updated results remain at `core_claim_plus`: Neo reduces table traffic by 50.8310% on the scaled temporal workload and saves 28.9147% traffic versus the no-deferred-depth ablation while preserving broad ordering structure.

## Stop Justification
- Completed at milestone `core_claim_plus`.
