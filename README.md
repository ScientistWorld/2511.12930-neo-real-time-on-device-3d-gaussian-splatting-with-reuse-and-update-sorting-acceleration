# Neo: Real-Time On-Device 3D Gaussian Splatting with Reuse-and-Update Sorting Acceleration

<!-- scope-note -->
> [!NOTE]
> **Not a full reproduction of the paper.** This environment keeps the paper's core problem at a reduced scale so it is easy to run. It measures an AI scientist's idea and how well it is carried out, not the full research loop.

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2511.12930"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2511.12930-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| **Paper ID** | [2511.12930](https://arxiv.org/abs/2511.12930) |
|:---|:---|
| **Domain** | Computer Architecture / Neural Rendering Acceleration |
| **TL;DR** | Neo accelerates on-device 3D Gaussian Splatting by reusing and incrementally updating per-tile Gaussian depth order across frames. |

## Summary

The paper identifies sorting as the dominant memory-bandwidth bottleneck for high-resolution 3DGS rendering on edge devices. Neo exploits temporal similarity across consecutive camera poses by updating prior sorted Gaussian tables instead of fully sorting every frame. The paper couples this algorithm with a specialized sorting/rasterization accelerator and reports large throughput and DRAM-traffic improvements with negligible image-quality loss.

## Problem

How can an on-device 3D Gaussian Splatting renderer maintain correct per-tile depth ordering across a sequence of camera poses while greatly reducing the memory traffic normally caused by sorting every tile from scratch for every frame?

## The paper's method

Neo introduces reuse-and-update sorting for 3D Gaussian Splatting and pairs it with hardware support for low-traffic on-device rendering. The core software-visible contribution is to carry forward each tile's sorted Gaussian table from the previous frame and update it incrementally instead of globally sorting from scratch.

## Key results of the paper

- QHD DRAM traffic for 60 frames drops from 104.6 GB on GSCore to 19.6 GB on Neo.
- Neo reports 99.3 FPS average QHD throughput and 5.6x speedup over GSCore.
- Rendering quality changes by at most 0.1 dB PSNR and 0.001 LPIPS across six scenes.

## Run it

```bash
pip install sciworld
sw research 2511.12930 --mode innovate --agent claude-code
sw evaluate 2511.12930
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

