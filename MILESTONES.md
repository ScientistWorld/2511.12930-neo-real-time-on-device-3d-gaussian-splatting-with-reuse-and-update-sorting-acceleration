# Reproduction Milestones

**Current: core_claim**

## Progress Log

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

## Stop Justification
- Completed at milestone `core_claim`. The paper's actual reuse-and-update sorting algorithm is implemented and validated on a scaled temporal 3DGS sorting benchmark.
