# Experiment Overview

## synthetic_temporal_sorting

Tests whether a system can exploit temporal similarity in per-tile Gaussian depth-ordering workloads to reduce sorting traffic while maintaining ordering quality. The experiment compares a candidate against exact full sorting on deterministic high-retention, moderate-retention, and rapid-motion temporal traces.

## deferred_depth_update_ablation

Tests whether a candidate can remove an extra table-refresh cost while preserving the same ordering quality. The comparison uses a normal candidate artifact and a paired artifact that charges the extra refresh work explicitly.

The official scores also include adjacent-pair and sampled-pair ordering checks. These are constraint diagnostics: they make it harder for a candidate to reduce traffic by returning an order that only passes broad sparse probes while scrambling local depth order.

`scoring/per_regime_scores.json` reports diagnostics for each temporal regime without entering the official `scores.json` contract. These diagnostics help identify whether gains hold on smooth high-retention motion, moderate churn, and rapid-motion stress traces.
