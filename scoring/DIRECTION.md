# Research Direction

## Research Problem

This benchmark focuses on reducing memory traffic for depth sorting in temporally adjacent 3D Gaussian Splatting frames while preserving the ordering quality needed for rendering.

## Core Contribution

The paper's contribution is incremental maintenance of per-tile Gaussian depth order across frames, plus accounting for the memory behavior of that maintenance. Improvements should remain in this family: temporal reuse, partial correction, incremental merge/delete/update, or closely related per-tile ordering maintenance.

## Approach Scope

Candidates may change how reused table regions are selected, how boundaries are shifted, how incoming entries are merged, how outgoing entries are compacted, or how stale metadata is handled. They may also propose alternate hardware-friendly traffic models if they preserve the same artifact contract and include comparable traffic accounting.

## Out of Bounds

Replacing the task with full sorting on more powerful hardware is out of scope. Ignoring ordering quality to reduce traffic is out of scope. Changing the workload so fewer Gaussians need sorting is out of scope for the existing experiment key. Image-space reuse, pruning, quantization, or retraining-only methods are out of scope unless they still solve the same per-tile sorting-maintenance problem.
