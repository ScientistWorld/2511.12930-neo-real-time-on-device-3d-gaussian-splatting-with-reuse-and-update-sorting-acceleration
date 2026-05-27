# Research Direction

## Research Problem

This benchmark focuses on reducing memory traffic for depth sorting in temporally adjacent 3D Gaussian Splatting frames while preserving the ordering quality needed for rendering.

## Core Contribution

The research direction is to maintain useful per-tile Gaussian depth order across related frames while substantially reducing table-entry memory traffic. Improvements should remain in this problem family: hardware-aware ordering maintenance for 3D Gaussian Splatting workloads with explicit traffic accounting.

## Approach Scope

Candidates may change the ordering-maintenance policy, update granularity, membership bookkeeping, metadata policy, or hardware-friendly traffic model. The artifact contract must stay comparable: each run should emit per-frame per-tile orders and enough traffic accounting for the reusable evaluator to score the same metrics.

## Out of Bounds

Replacing the task with full sorting on more powerful hardware is out of scope. Ignoring ordering quality to reduce traffic is out of scope. Changing the workload so fewer Gaussians need sorting is out of scope for the existing experiment key. Image-space reuse, pruning, quantization, or retraining-only methods are out of scope unless they still solve the same per-tile depth-ordering problem and report comparable traffic.
