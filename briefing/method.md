# Paper's Method

## Key Contribution

Neo introduces reuse-and-update sorting for 3D Gaussian Splatting and pairs it with hardware support for low-traffic on-device rendering. Instead of building and globally sorting every tile's Gaussian table from scratch every frame, it carries each tile's sorted table forward from the previous frame and corrects it incrementally.

## Approach

Per frame and tile, in a single off-chip pass over the reused table (Sec. 4.3, 5.3):

1. **Reordering with Dynamic Partial Sorting (Algorithm 1).** The table is streamed through the sorting engine in chunks of at most 256 entries that are sorted on chip. Chunk boundaries alternate between frames: odd frames use `[0,C), [C,2C), ...`, even frames shift every boundary by `C/2` so entries can migrate across the previous boundaries over successive frames (Fig. 9b).
2. **Insertion.** Preprocessing emits only the newly visible ("incoming") Gaussians of the tile; they are sorted on chip and merged into the reordered stream by the merge unit (MSU+).
3. **Deletion.** Entries whose valid bit was cleared by the previous frame's rasterization (no longer intersecting the tile) are dropped during the same merge, avoiding a separate shifting pass.
4. **Deferred depth update.** During rasterization, the engine writes each Gaussian's current depth and valid bit back into the table, so the next frame sorts on depths that are one frame stale but never pays for a separate depth-refresh pass (Sec. 4.4; without it, traffic rises by 33.2-35.8%).

## In this gym

`method/neo_policy.py` (registered as `policies/neo_reuse_update.json`) issues exactly this schedule: one `pass` per tile and frame with Algorithm 1's interleaved 256-entry cuts and `merge: true`, relying on the hardware's deferred depth update. The evaluator's memory model executes the operations (chunk sorting, merging with incoming Gaussians, valid-bit deletion, depth write-back) and charges their traffic. The paper's Algorithm 1 pseudo-code, read literally, would leave gaps on even frames; the implementation follows the text and Fig. 9b (boundaries shifted by half a chunk, every entry covered).

## Main Claims

- 81.3% lower QHD DRAM traffic than GSCore (94.4% lower than Orin AGX) over 60 frames.
- At most 0.1 dB PSNR and 0.001 LPIPS degradation versus the original 3DGS rendering.
- The deferred depth update removes 33-36% of the remaining traffic.
- Real-time throughput is maintained under 2x-16x faster camera movement and on large scenes.
- Hardware claims (throughput, area, power) are outside this gym.
