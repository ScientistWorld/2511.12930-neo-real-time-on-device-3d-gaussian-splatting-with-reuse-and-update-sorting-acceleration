# Experiment Overview

## synthetic_temporal_sorting

Tests whether a system can exploit temporal similarity in per-tile Gaussian depth-ordering workloads to reduce sorting traffic while maintaining ordering quality. The experiment compares a candidate against exact full sorting on deterministic high-retention, moderate-retention, and rapid-motion temporal traces.

## Per-Regime Diagnostics

`scoring/per_regime_scores.json` reports the same comparison for each temporal regime without entering the official `scores.json` contract: `family_like` for smooth high-retention camera movement, `train_like` for moderate retention with more incoming/outgoing entries, and `rapid_motion` for a stress case with stronger rank drift.

## deferred_depth_update_ablation

Tests whether avoiding a separate post-render depth-refresh pass materially reduces traffic while preserving the same ordering quality. The comparison isolates the full candidate method from an otherwise identical variant that performs the extra refresh work explicitly.
