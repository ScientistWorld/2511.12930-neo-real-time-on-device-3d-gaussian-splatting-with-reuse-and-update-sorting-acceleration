# Progress

## What Works

- Paper-specific briefing, scoring targets, constraints, and direction files are filled in.
- `data/synthetic_workload.py` creates deterministic temporal per-tile Gaussian table traces with high-retention, moderate-retention, and rapid-motion settings.
- `method/neo_sort.py` implements the paper's reuse-and-update sorting algorithm: chunk-local Dynamic Partial Sorting, interleaved boundaries, incoming insertion, outgoing deletion, and deferred depth update.
- `baseline/full_sort.py` implements exact full per-frame sorting.
- `eval/evaluate_sorting.py` reads output artifacts only and writes `scoring/scores.json`.
- `bash scripts/reproduce.sh` completed locally and `python validate.py --compare` passed.

## Results

- Paper QHD memory result: GSCore 104.6 GB for 60 frames, Neo 19.6 GB, 81.3% reduction.
- Scaled synthetic benchmark result: full sort 33.1776 MB, Neo reuse-and-update 15.0555 MB, 54.6215% reduction.
- Ordering constraints on the scaled benchmark: broad pair-order accuracy 1.0, mean absolute rank error 1.6629, p99 rank error 6.2778.

## Remaining

- Run the packaged reproduction as a scheduler job. If the job reproduces the local result, update milestone to `core_claim`.
- Higher milestones would require trained 3DGS scenes or a more detailed hardware/cycle simulator. The paper's RTL/cycle simulator and trained scene checkpoints were not released with the paper.

## Issues

- The paper does not provide a public Neo implementation, RTL, cycle simulator, or exact trained 3DGS scene artifacts.
- The reproduction therefore uses a deterministic synthetic temporal Gaussian-table workload and traffic/order metrics rather than image PSNR/LPIPS from rendered scenes.

## Deviations from Paper

- **Dataset/artifacts:** The paper used trained 3DGS scenes from Tanks and Temples and Mill 19. This workspace uses deterministic synthetic per-tile Gaussian visibility/depth traces because the trained Gaussian checkpoints and authors' simulator are not released.
- **Scale:** The paper evaluates millions of Gaussians and 60 rendered frames at HD/FHD/QHD. This reproduction uses smaller per-tile traces that preserve temporal retention, rank drift, incoming, and outgoing behavior so CPU test jobs remain lightweight.
- **Metrics:** The paper reports FPS, DRAM traffic, PSNR, and LPIPS. This reproduction measures table-entry traffic and depth-order preservation. It cannot measure image PSNR/LPIPS without rendered scenes and a full 3DGS renderer.
