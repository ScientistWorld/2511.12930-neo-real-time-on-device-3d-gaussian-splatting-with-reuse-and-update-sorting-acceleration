# Evaluation Targets

Run all targets with `bash scripts/evaluate_train.sh` (visible scenes) or `bash scripts/evaluate_test.sh` (held-out scenes); both score every manifest in `policies/` plus the built-in `full_sort` baseline.

## Primary: synthetic_temporal_sorting

Sorting-stage DRAM traffic saved relative to an exact full re-sort under normal camera motion.
- **Metric**: `traffic_reduction_pct` (higher is better)

## Constraint: synthetic_temporal_sorting

Rendering quality is preserved: the ordering error must not visibly change the image (paper: at most 0.1 dB PSNR). Runs above 0.1 dB fail.
- **Metric**: `psnr_drop_db` (lower is better)

## Constraint: synthetic_temporal_sorting

Gaussians stay close to their exact depth rank.
- **Metric**: `mean_abs_rank_error` (lower is better)

## Secondary: rapid_camera_motion

Traffic saved when the camera moves twice as fast (paper Fig. 17b setting).
- **Metric**: `traffic_reduction_pct` (higher is better)

## Constraint: rapid_camera_motion

Rendering quality under rapid motion. Runs above 1.0 dB fail.
- **Metric**: `psnr_drop_db` (lower is better)

## Constraint: rapid_camera_motion

Ordering fidelity under rapid motion.
- **Metric**: `mean_abs_rank_error` (lower is better)
