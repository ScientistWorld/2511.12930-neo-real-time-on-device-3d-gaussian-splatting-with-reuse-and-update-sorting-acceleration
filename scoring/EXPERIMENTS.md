# Experiment Overview

## synthetic_temporal_sorting

Tests whether a system can reduce traffic for per-tile Gaussian depth-ordering workloads across adjacent frames while maintaining ordering quality. The experiment compares a candidate against exact full sorting on deterministic high-retention, moderate-retention, and rapid-motion temporal traces.

## deferred_depth_update_ablation

Tests a paired traffic-accounting target. A candidate is compared with a second artifact that includes an explicit extra table-refresh charge, so the score captures traffic saved by avoiding that charge without changing the workload or ordering-quality target.

The official scores also include adjacent-pair and sampled-pair ordering checks. These are constraint diagnostics: they make it harder for a candidate to reduce traffic by returning an order that only passes broad sparse probes while scrambling local depth order.

`scoring/per_regime_scores.json` reports diagnostics for each temporal regime without entering the official `scores.json` contract. These diagnostics help identify whether gains hold on smooth high-retention motion, moderate churn, and rapid-motion stress traces.
