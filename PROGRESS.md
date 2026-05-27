# Progress

## What Works

- Paper-specific briefing, scoring targets, constraints, and direction files are filled in.
- `data/synthetic_workload.py` creates deterministic temporal per-tile Gaussian table traces with high-retention, moderate-retention, and rapid-motion settings.
- `method/neo_sort.py` implements the paper's reuse-and-update sorting algorithm: chunk-local Dynamic Partial Sorting, interleaved boundaries, incoming insertion, outgoing deletion, and deferred depth update.
- `baseline/full_sort.py` implements exact full per-frame sorting.
- `eval/evaluate_sorting.py` reads output artifacts only and writes `scoring/scores.json`.
- `bash scripts/reproduce.sh` completed locally and `python validate.py --compare` passed.
- Scheduler CPU test job `a5d0ec7a-e50` completed successfully inside the container and passed validation.
- Local rerun at 2026-05-27 02:05 UTC again completed `bash scripts/reproduce.sh` and `python validate.py --compare` successfully.
- Audit found that the old evaluator trusted method-reported summary metrics. This is fixed: artifacts now include per-frame, per-tile predicted orders and `eval/` recomputes ordering quality from the workload.
- Local rerun at 2026-05-27 02:09 UTC completed `bash scripts/reproduce.sh` and `python validate.py --compare` successfully with the independent evaluator.
- Scheduler CPU test job `597e7566-ff8` completed successfully inside the container with the independent evaluator and passed `python validate.py --compare`.
- Per-regime diagnostics cover high-retention, moderate-retention, and rapid-motion traces, reaching `core_claim_plus`.
- Continuation audit on 2026-05-27 found the implementation to be a real scaled version of Neo's sorting algorithm, not a surrogate. The audit also found that root `README.md` and `manifest.json` are read-only bind mounts to `devtmpfs[/null]`; they cannot be replaced from inside this container and have been excluded from the working diff.
- Added `deferred_depth_update_ablation`: `method/neo_sort.py` can now run a no-deferred-depth variant that charges a separate depth refresh pass, and `eval/evaluate_sorting.py` scores it from artifacts without importing method code.
- Local rerun at 2026-05-27 02:18 UTC completed `bash scripts/reproduce.sh`, `bash scripts/evaluate.sh`, and `python validate.py --compare` successfully with both scored experiments.
- Scheduler CPU test job `aff60dc0-5e4` completed successfully inside the container at 2026-05-27 02:23 UTC. It ran `bash scripts/run.sh`, wrote the two-experiment `scoring/scores.json`, and passed `python validate.py --compare`.
- Tightened the simulator on 2026-05-27 02:53 UTC so outgoing Gaussians are carried with a `valid` bit from the rasterization-like visibility update and deleted in the next merge step, matching the paper's deferred deletion flow more closely than the earlier current-membership oracle.
- Extended the official evaluator to report adjacent-pair, sampled-pair, and deferred-update MB metrics in `scoring/scores.json`, then reran `bash scripts/reproduce.sh`, `bash scripts/evaluate_train.sh`, `bash scripts/evaluate_test.sh`, and `python validate.py --compare` locally.
- Final verification on 2026-05-27 03:08 UTC made `scripts/evaluate.sh` discover generic candidate artifacts, tightened method-agnostic scoring documentation, adjusted the ablation primary metric to the scale-normalized savings percentage, and reran `bash scripts/reproduce.sh` plus `python validate.py --compare` successfully.

## Results

- Paper QHD memory result: GSCore 104.6 GB for 60 frames, Neo 19.6 GB, 81.3% reduction.
- Scaled synthetic benchmark result after valid-bit deletion: full sort 33.1776 MB, Neo reuse-and-update 16.3131 MB, 50.8310% reduction.
- Deferred-depth ablation result: no-deferred Neo uses 22.9486 MB, while full Neo uses 16.3131 MB, a 28.9147% traffic saving from the deferred depth update path on the scaled workload.
- Ordering constraints recomputed independently from predicted per-tile orders: pair-order accuracy 0.9091, adjacent-pair accuracy 0.6580, sampled-pair accuracy 0.9636, mean absolute rank error 1.6862, p99 rank error 6.3403.
- Per-regime diagnostics in `scoring/per_regime_scores.json`: high-retention 54.55% traffic reduction, moderate-retention 51.82%, rapid-motion 46.42%; sampled-pair accuracy remains above 0.936 in all regimes.
- The same results were reproduced by the completed scheduler job.

## Remaining

- Higher milestones would require trained 3DGS scenes or a more detailed hardware/cycle simulator. The paper's RTL/cycle simulator and trained scene checkpoints were not released with the paper.
- No further productive expansion is available in this workspace without trained 3DGS scenes, the authors' simulator, or hardware RTL.

## Issues

- The paper does not provide a public Neo implementation, RTL, cycle simulator, or exact trained 3DGS scene artifacts.
- The reproduction therefore uses a deterministic synthetic temporal Gaussian-table workload and traffic/order metrics rather than image PSNR/LPIPS from rendered scenes.
- Root `README.md` and `manifest.json` are mounted from read-only `devtmpfs[/null]` in this runtime. Attempts to remove or replace them fail with `Device or resource busy`, so they remain outside the reproducible code path.

## Deviations from Paper

- **Dataset/artifacts:** The paper used trained 3DGS scenes from Tanks and Temples and Mill 19. This workspace uses deterministic synthetic per-tile Gaussian visibility/depth traces because the trained Gaussian checkpoints and authors' simulator are not released.
- **Scale:** The paper evaluates millions of Gaussians and 60 rendered frames at HD/FHD/QHD. This reproduction uses smaller per-tile traces that preserve temporal retention, rank drift, incoming, and outgoing behavior so CPU test jobs remain lightweight.
- **Metrics:** The paper reports FPS, DRAM traffic, PSNR, and LPIPS. This reproduction measures table-entry traffic and depth-order preservation. It cannot measure image PSNR/LPIPS without rendered scenes and a full 3DGS renderer.
