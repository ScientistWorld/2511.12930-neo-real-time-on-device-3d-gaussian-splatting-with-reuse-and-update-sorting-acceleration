# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-05-27 02:20] - none
- Started reproduction of Neo from paper markdown.
- Identified the core reproducible algorithm: reuse-and-update sorting for per-tile 3DGS Gaussian tables.

### [2026-05-27 02:55] - method_runs
- Implemented Dynamic Partial Sorting with alternating half-chunk boundaries, insertion, deletion, and deferred depth refresh in `method/neo_sort.py`.
- Implemented full per-frame sorting baseline and method-agnostic evaluator.
- Local CPU reproduction runs end-to-end and writes `scoring/scores.json`.

## Stop Justification
- Not stopped. Submitting a CPU test job to verify the packaged environment before claiming `core_claim`.
