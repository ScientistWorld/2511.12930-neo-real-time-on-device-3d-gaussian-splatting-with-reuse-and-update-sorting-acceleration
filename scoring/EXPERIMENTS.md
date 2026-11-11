# Experiment Overview

Both experiments run every registered method on the same procedurally generated 3D Gaussian scenes, frame by frame, and compare it with an exact full re-sort performed by the evaluator on the same hardware model. Every number is computed by the evaluator; methods only choose sorting-engine operations.

## synthetic_temporal_sorting (weight 0.6)

The paper's main claim: across consecutive frames of normal head motion, a tile-based renderer can keep its per-tile depth order nearly exact while moving far fewer table entries through DRAM than re-sorting every tile from scratch. The camera motion is calibrated so that tile membership changes between frames as much as in the paper's real captures. The experiment rewards traffic saved and penalizes any visible rendering degradation; a degradation beyond what the paper reports (0.1 dB PSNR) fails the run.

## rapid_camera_motion (weight 0.4)

The paper's stress study: the same kind of scenes with the camera moving twice as fast, so far fewer Gaussians stay in a tile from one frame to the next and depths change more. It tests whether traffic savings and image quality survive when temporal similarity drops. This is where approaches that rely on frame-to-frame similarity lose quality, so it carries most of the room for improvement. A degradation beyond 1.0 dB PSNR fails the run.

## Metrics (both experiments)

- `traffic_reduction_pct`: sorting-stage DRAM traffic saved relative to the exact full re-sort (benefit).
- `psnr_drop_db`: rendering-quality loss caused by ordering errors, expressed at the paper's mean reconstruction PSNR (constraint).
- `mean_abs_rank_error`: how far Gaussians sit from their exact depth rank (ordering fidelity, lower weight).

`scoring/diagnostics_{train,test}.json` adds per-scene values, absolute traffic in MB, and the traffic the same run would need if depth write-back were a separate pass.
