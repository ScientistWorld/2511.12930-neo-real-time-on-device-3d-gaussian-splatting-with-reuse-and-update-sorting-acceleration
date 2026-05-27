# Train/Test Evaluation Design Notes

## Checked

- Read `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side. Train calls `eval/train/evaluate.py` and defaults to `scoring/scores_train.json`; test calls `eval/test/evaluate.py` and defaults to `scoring/scores_test.json`.
- Checked for hardcoded method defaults. Both scripts accept explicit artifacts and otherwise discover compatible `outputs/*.json` artifacts.
- Checked evaluator attachment to method outputs. Both slices read method artifacts and workload data; they do not import or run `method/`.
- Checked train/test leakage with grep. There are no Python cross-imports between `eval/train/` and `eval/test/`; the test script only optionally reads `scoring/scores_train.json` to restrict method names.
- Checked paper-agreement metric names. No active metric is a reproduction-error or published-value matching metric.
- Confirmed `scoring/scores_train.json` and `scoring/scores_test.json` are absent.
- Ran `bash -n` on both split scripts.

## Changed

- Fixed an omission shortcut in both evaluators: a candidate artifact must now cover every frame in the slice and every tile in each scored frame. Previously, an artifact could omit hard frames or tiles, lower reported traffic, and get perfect quality on the remaining partial slice.
- Added `adjacent_pair_accuracy` to catch local near-neighbor order scrambling that sparse pair probes could miss.
- Added `sampled_pair_order_accuracy`, a deterministic sampled Kendall-style pair metric, to broaden order checking without all-pairs cost.
- Added the new metrics to both official experiments in `scoring/reference.json`.
- Added required `description` fields to all active metrics in `scoring/reference.json` and adjusted coefficients so traffic reduction remains primary while ordering quality is triangulated across local, sampled, sparse, mean-error, and tail-error views.

## Runtime Concerns For Runner Iteration

- The stricter coverage check should be exercised on the existing artifacts during the next runner pass. It is expected to pass if artifacts contain all workload frames and tiles.
- The new quality metrics may be near-saturated for exact or near-exact methods. They are still useful against shortcut artifacts, but the next runner should inspect train/test spread to ensure they are not all constant across candidate methods.
- The test slice is still a disjoint frame split over the same workload, not a new hidden workload. It mainly detects overfitting to visible frame rules or partial-output shortcuts, not methods that memorize the public workload while preserving the artifact contract.

## Runner Iteration Notes

- First scoring job produced `scoring/scores_train.json` and then failed in the held-out evaluator because the test split included frame 0, while all artifacts begin at update frame 1. Adjusted `eval/test/evaluate.py` so the held-out slice remains disjoint but only scores update frames (`frame_idx > 0 and frame_idx % 4 in {0, 3}`).
- Second scoring job completed. The produced train/test files had useful traffic, adjacent-order, and rank-error signal, but the sparse `pair_order_accuracy` and original sampled pair metric were saturated at 1.0 for every method on both slices. Revised `sampled_pair_order_accuracy` into a deterministic multi-scale local/long-range pair probe and set the saturated sparse pair metric to zero weight in `scoring/reference.json`.
