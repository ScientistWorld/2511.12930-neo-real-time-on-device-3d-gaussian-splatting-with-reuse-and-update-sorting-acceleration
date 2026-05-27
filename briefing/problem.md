# Problem Definition

## Research Question

How can an on-device 3D Gaussian Splatting renderer maintain correct per-tile depth ordering across a sequence of camera poses while greatly reducing the memory traffic normally caused by sorting every tile from scratch for every frame?

## Why It Matters

High-resolution AR/VR rendering needs low latency and high frame rate on memory-constrained devices. In 3DGS, depth sorting can dominate off-chip traffic, so reducing sorting traffic without corrupting visual order is necessary for practical on-device rendering.

## Success Criteria

A successful solution should process temporally adjacent per-tile Gaussian tables, reduce sorting-related traffic relative to full per-frame sorting, and preserve near-correct depth order so rendering quality is not meaningfully degraded.
