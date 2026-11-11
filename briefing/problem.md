# Problem Definition

## Research Question

How can an on-device 3D Gaussian Splatting (3DGS) renderer keep each screen tile's Gaussians in correct front-to-back depth order across a sequence of camera poses, while moving far fewer table entries through DRAM than re-sorting every tile from scratch every frame?

## Why It Matters

High-resolution AR/VR rendering must run at high frame rate on devices with little memory bandwidth. In tile-based 3DGS, every frame duplicates each visible Gaussian into the tiles it overlaps and sorts every tile's table by depth before alpha blending. That sorting stage dominates off-chip traffic. Consecutive frames are highly similar, but blending in the wrong order changes the rendered image, so traffic can only be saved where image quality is preserved.

## Setting

A sorting engine with a small on-chip buffer (256 table entries) maintains one depth-ordered table per 64x64-pixel tile in DRAM. Each table entry is 8 bytes (Gaussian id and depth). Each frame some Gaussians enter a tile and some leave it, and the depths of the others change as the camera moves. The engine can only reorder data that it streams through its buffer. After sorting, the rasterizer blends each tile's Gaussians in table order.

## Success Criteria

A successful solution, measured on scenes it has never seen:

- moves substantially fewer table entries per frame than an exact full re-sort on the same hardware, and
- renders images whose quality is practically indistinguishable from exact depth order, both under normal head motion and under much faster camera movement.
