# Overview

- **Paper ID:** 2511.12930
- **Title:** Neo: Real-Time On-Device 3D Gaussian Splatting with Reuse-and-Update Sorting Acceleration
- **Domain:** Computer Architecture / Neural Rendering Acceleration
- **TL;DR:** Neo accelerates on-device 3D Gaussian Splatting by reusing and incrementally updating per-tile Gaussian depth order across frames.

## Short Summary

The paper identifies sorting as the dominant memory-bandwidth bottleneck for high-resolution 3DGS rendering on edge devices. Neo exploits temporal similarity across consecutive camera poses by updating prior sorted Gaussian tables instead of fully sorting every frame. The paper couples this algorithm with a specialized sorting/rasterization accelerator and reports large throughput and DRAM-traffic improvements with negligible image-quality loss.

## Key Results

- QHD DRAM traffic for 60 frames drops from 104.6 GB on GSCore to 19.6 GB on Neo.
- Neo reports 99.3 FPS average QHD throughput and 5.6x speedup over GSCore.
- Rendering quality changes by at most 0.1 dB PSNR and 0.001 LPIPS across six scenes.
