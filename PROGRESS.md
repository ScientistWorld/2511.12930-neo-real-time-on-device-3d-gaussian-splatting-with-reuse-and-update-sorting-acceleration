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

## Results

- Paper QHD memory result: GSCore 104.6 GB for 60 frames, Neo 19.6 GB, 81.3% reduction.
- Scaled synthetic benchmark result after consistent post-seed accounting: full sort 33.1776 MB, Neo reuse-and-update 14.6131 MB, 55.9549% reduction.
- Deferred-depth ablation result: no-deferred Neo uses 21.2486 MB, while full Neo uses 14.6131 MB, a 31.2280% traffic saving from the deferred depth update path on the scaled workload.
- Ordering constraints recomputed independently from predicted per-tile orders: broad pair-order accuracy 1.0, mean absolute rank error 1.6865, p99 rank error 6.3502.
- Per-regime diagnostics in `scoring/per_regime_scores.json`: high-retention 57.60% traffic reduction, moderate-retention 56.39%, rapid-motion 54.01%; all preserve pair-order accuracy 1.0.
- The same results were reproduced by the completed scheduler job.

## Remaining

- Higher milestones would require trained 3DGS scenes or a more detailed hardware/cycle simulator. The paper's RTL/cycle simulator and trained scene checkpoints were not released with the paper.
- A scheduler CPU test is being submitted to validate the new ablation inside the packaged environment.
- Beyond that, further productive expansion would require trained 3DGS scenes, the authors' simulator, or hardware RTL.

## Issues

- The paper does not provide a public Neo implementation, RTL, cycle simulator, or exact trained 3DGS scene artifacts.
- The reproduction therefore uses a deterministic synthetic temporal Gaussian-table workload and traffic/order metrics rather than image PSNR/LPIPS from rendered scenes.
- Root `README.md` and `manifest.json` are mounted from read-only `devtmpfs[/null]` in this runtime. Attempts to remove or replace them fail with `Device or resource busy`, so they remain outside the reproducible code path.

## Deviations from Paper

- **Dataset/artifacts:** The paper used trained 3DGS scenes from Tanks and Temples and Mill 19. This workspace uses deterministic synthetic per-tile Gaussian visibility/depth traces because the trained Gaussian checkpoints and authors' simulator are not released.
- **Scale:** The paper evaluates millions of Gaussians and 60 rendered frames at HD/FHD/QHD. This reproduction uses smaller per-tile traces that preserve temporal retention, rank drift, incoming, and outgoing behavior so CPU test jobs remain lightweight.
- **Metrics:** The paper reports FPS, DRAM traffic, PSNR, and LPIPS. This reproduction measures table-entry traffic and depth-order preservation. It cannot measure image PSNR/LPIPS without rendered scenes and a full 3DGS renderer.
