# Paper's Method

## Key Contribution

Neo introduces reuse-and-update sorting for 3D Gaussian Splatting and pairs it with hardware support for low-traffic on-device rendering. The core software-visible contribution is to carry forward each tile's sorted Gaussian table from the previous frame and update it incrementally instead of globally sorting from scratch.

## Approach

For each frame and tile, Neo performs four operations. First, it reorders the previous Gaussian table with Dynamic Partial Sorting: entries are sorted in chunks of up to 256 Gaussians, and chunk boundaries alternate by half a chunk across frames so entries can migrate across prior boundaries. Second, newly visible Gaussians are sorted and inserted. Third, outgoing Gaussians are deleted during the merge. Fourth, depth values are refreshed during rasterization so the next frame can reuse the updated table without an extra random depth-fetch pass.

The hardware design contains preprocessing, sorting, and rasterization engines. The sorting engine includes bitonic sorting and merge units for chunk sorting, insertion, and deletion; the rasterization engine supports subtile rasterization and on-the-fly depth/valid-bit update.

## Main Claims

The primary claim is that temporal reuse of sorted Gaussian tables greatly reduces sorting-induced memory traffic while preserving rendering quality. The paper reports 81.3% lower QHD DRAM traffic than GSCore and 94.4% lower than Orin AGX for 60 frames, with less than 0.1 dB PSNR and 0.001 LPIPS degradation.

Secondary claims include higher end-to-end throughput than Orin AGX and GSCore, robustness to larger scenes and rapid camera movement, and small hardware area/power overhead.
