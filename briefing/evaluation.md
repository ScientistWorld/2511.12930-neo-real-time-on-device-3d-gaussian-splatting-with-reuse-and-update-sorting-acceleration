# Evaluation

## Metrics

The benchmark measures memory traffic and ordering quality over a deterministic temporal sequence of per-tile Gaussian tables.

`traffic_MB` estimates table-entry memory traffic; lower is better. `traffic_reduction_pct` compares a candidate against full per-frame sorting; higher is better. `pair_order_accuracy` checks deterministic broad pair relationships in each output order against exact depth-sorted order; higher is better. `adjacent_pair_accuracy` and `sampled_pair_order_accuracy` add local and odd-offset ordering checks. `mean_abs_rank_error` and `p99_abs_rank_error` measure displacement from exact depth rank; lower is better.

## Baselines and Targets

The reference baseline is full sorting of each tile at each frame, which has perfect ordering but high memory traffic. The published QHD, 60-frame reference point reports 104.6 GB for full sorting and 19.6 GB for the target result, an 81.3% reduction, while image-quality changes remain under 0.1 dB PSNR and 0.001 LPIPS. This reproduction uses ordering-quality proxies instead of image PSNR because trained 3DGS scene checkpoints are not released.

## Evaluation Protocol

Run `bash scripts/reproduce.sh` to generate the deterministic workload, produce the full-sort baseline artifact, produce candidate artifacts, and write `scoring/scores.json`. Evaluation code in `eval/` reads per-tile predicted-order artifacts under `outputs/`, recomputes ordering quality against the workload, and must not import candidate method code. Workload generation uses a fixed seed and three temporal settings: high-retention, moderate-retention, and rapid-motion.
