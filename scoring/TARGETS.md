# Evaluation Targets

## Primary: synthetic_temporal_sorting

Tests whether a candidate reduces per-tile sorting traffic across temporally adjacent Gaussian-table frames.
- **Metric**: `traffic_reduction_pct` (higher is better)
- **Run**: `bash scripts/reproduce.sh`

## Constraint: synthetic_temporal_sorting

Tests whether the traffic reduction preserves near-correct depth ordering rather than simply skipping sorting work.
- **Metric**: `pair_order_accuracy` (higher is better)
- **Run**: `bash scripts/reproduce.sh`

## Constraint: synthetic_temporal_sorting

Tests worst-case rank displacement under temporal motion.
- **Metric**: `p99_abs_rank_error` (lower is better)
- **Run**: `bash scripts/reproduce.sh`

## Secondary: deferred_depth_update_ablation

Tests whether a candidate avoids an extra table-refresh pass without changing the workload or degrading ordering quality.
- **Metric**: `deferred_update_savings_pct` (higher is better)
- **Run**: `bash scripts/reproduce.sh`
