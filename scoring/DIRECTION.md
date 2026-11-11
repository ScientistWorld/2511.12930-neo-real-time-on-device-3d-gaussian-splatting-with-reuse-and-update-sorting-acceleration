# Research Direction

## Research Problem

Keep per-tile Gaussian depth order correct across consecutive frames of a 3D Gaussian Splatting renderer while minimizing sorting-stage DRAM traffic on a sorting engine with a small on-chip buffer.

## Core Contribution

Exploit temporal similarity between frames so that most of the per-frame sorting work and memory traffic of a full re-sort can be avoided without visible change in the rendered image.

## Approach Scope

Within the fixed hardware model, a method may change anything about which operations run and when: how tables are reused or rebuilt, how and where they are reordered, how many passes and over which ranges, when stored depths are refreshed, how incoming Gaussians are inserted, and how all of this adapts to the per-tile counts and rasterizer feedback. Improvements can come from lower traffic at equal quality, from better quality at equal traffic, or from staying robust when the camera moves fast.

## Out of Bounds

Changing the hardware model, the operation costs, the scenes, the frame count, the baseline or the quality limits; obtaining hidden scene data; trading visible image quality beyond the stated limits for traffic.
