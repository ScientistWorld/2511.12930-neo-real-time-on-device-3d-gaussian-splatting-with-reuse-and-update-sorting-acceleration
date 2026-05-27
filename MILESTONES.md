# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

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
