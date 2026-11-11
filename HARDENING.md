# Hardening report (iteration 11)

## Verdict

Better results now score higher, and every major shortcut in `REDTEAM.md` is closed. The red-team audit found eight shortcuts that beat the reference; all of them relied on the evaluator trusting method-written artifacts (orders, traffic counts, comparison partners, workload, method/experiment selection). The gym now uses an **evaluator-owned protocol**:

- A method is a program registered by `policies/<name>.json`.
- `eval/{train,test}/evaluate.py` generates every scene itself and starts the method once per scene. It then drives the method frame by frame over stdin/stdout.
- The method never sees Gaussian ids, depths or orders. It only chooses sorting-engine operations: reuse/regenerate, chunked partial-sort passes, refreshes, merges.
- The evaluator executes those operations on its own memory model, counts their DRAM traffic and renders sampled pixels of every tile in the resulting order. It scores the rendering against exact depth order. Nothing a method writes is read back.

The paper's quality constraint is now measured as a PSNR drop of the rendered image and gated at the paper's 0.1 dB. Under normal motion, removing the paper's partial-sorting step now fails that gate.

In this iteration I also:

- closed two remaining evaluator-level loopholes (the evaluator-abort and stall shortcuts below),
- re-set the metric coefficients so that brute force can no longer outrank the reference,
- made failed runs receive each experiment's quality limit as their worst PSNR drop. With the old 10 dB value, failures dominated the normalisation spread and quality gains between passing methods became invisible.

All numbers below are from check job `75411634-63f`. It ran the final code: the official reference runs and the whole audit population through the unchanged hidden-test evaluator, plus the honest variants through train. Evidence is in `hardening/results/`.

## How ranks are computed here

The rank follows the task statement: `rank = Σ_exp w_exp Σ_metric |coef| · dir · (m − m_ref) / sd_pop`. Here `dir` is the metric's better direction, and `sd_pop` is the metric's spread over the attempts ranked together. That future population is unknown, so `hardening/rank_report.py` reports three populations:

- **A**: every audited entry. Failed runs carry their worst values.
- **H**: the honest entries that pass the quality limits: the reference, the variants, brute force and the built-in baseline.
- **P2**: each entry normalised against the reference alone. With two attempts every metric difference becomes ±2 sd, so only the coefficients and the signs matter.

## Do better results score higher?

The test numbers are traffic_reduction_pct / psnr_drop_db / mean_abs_rank_error. The rank triples are A / H / P2.

- **"Before"** uses the iteration-11 protocol with the old coefficients (1.0 / 1.0 / 0.25 in both experiments) and failed runs at 10 dB.
- **"After"** uses the final coefficients and failure rule.

| method | normal motion (test) | rapid motion (test) | Δrank before | Δrank after |
|---|---|---|---|---|
| `neo_reuse_update` (reference) | 68.01 / 0.0184 / 9.63 | 43.49 / 0.1594 / 22.81 | 0 | 0 |
| `better_drift_compensated` | 68.01 / 0.0146 / 3.57 | 43.49 / 0.0482 / 7.94 | +0.019 / +0.991 / +2.500 | **+0.078 / +0.471 / +1.040** |
| `better_drift_compensated_hybrid` | 67.17 / 0.0125 / 4.22 | 39.60 / 0.0402 / 9.85 | −0.012 / +0.929 / +0.500 | +0.060 / +0.373 / −0.960 |
| `tradeoff_hybrid_refresh` | 67.17 / 0.0134 / 7.82 | 39.60 / 0.0520 / 12.09 | −0.016 / +0.678 / +0.500 | +0.049 / +0.267 / −0.960 |
| `tradeoff_current_depth_refresh` | 57.39 / 0.0000 / 1.25 | 30.89 / 0.0009 / 5.45 | −0.133 / +1.236 / +0.500 | +0.004 / +0.208 / −0.960 |
| `weaker_fixed_boundaries` | 68.01 / 0.0184 / 9.62 | 43.49 / 0.1590 / 22.83 | +0.000 / +0.003 / +2.100 | +0.000 / +0.001 / +0.880 |
| `tradeoff_adaptive_extra_pass` | 47.48 / 0.0183 / 8.65 | 19.09 / 0.1585 / 21.14 | −0.309 / −1.053 / +0.500 | −0.310 / −1.091 / −0.960 |
| `weaker_extra_pass` | 46.72 / 0.0183 / 8.65 | 18.13 / 0.1585 / 21.14 | −0.321 / −1.096 / +0.500 | −0.321 / −1.134 / −0.960 |
| `weaker_periodic_full_sort` | 50.26 / 0.0647 / 8.87 | 32.96 / 0.3477 / 18.36 | −0.222 / −2.992 / −3.500 | −0.494 / −1.601 / −2.640 |
| `weaker_no_partial_sort` (fails: 0.743 dB normal motion) | failed | failed | −4.687 / fail / −4.500 | −3.177 / fail / −3.040 |
| `brute_force_exact_full_sort` | 0.00 / 0.0000 / 0.00 | 0.00 / 0.0000 / 0.00 | −0.770 / −0.828 / **+0.500** | −0.634 / −1.926 / −0.960 |
| `full_sort` (built-in baseline) | 0.00 / 0.0000 / 0.00 | 0.00 / 0.0000 / 0.00 | −0.770 / −0.828 / **+0.500** | −0.634 / −1.926 / −0.960 |

What the variants do:

- **`better_drift_compensated`** is a genuinely better method at no extra cost. It maps the fresh incoming depths onto the table's one-frame-stale depth scale before merging, using the rasterizer's per-tile affine depth fit. Traffic is identical to the reference, and quality is better on every test scene of both experiments (paired, per scene):
  - normal motion: PSNR drop −0.0001 to −0.0140 dB, rank error −2.1 to −12.1;
  - rapid motion: PSNR drop −0.045 to −0.278 dB, rank error −11.8 to −18.3.

  The evaluator is deterministic, so there is no seed noise; the gap is consistent across all 8 paired scenes. It ranks above the reference in every population, before and after.
- **Weaker variants** rank below the reference in every population after the fix:
  - `weaker_extra_pass`: a second partial-sort pass. It costs about 21 pp of traffic for no quality gain, which matches the paper's "additional passes provide marginal benefit".
  - `weaker_periodic_full_sort`: the paper's periodic-sorting alternative. It saves less traffic and its quality degrades more (0.065 / 0.348 dB), matching Fig. 19.
  - `weaker_no_partial_sort`: drops the paper's Dynamic Partial Sorting and now fails the quality limit.

  Before the coefficient fix, the extra-pass and adaptive variants outranked the reference in P2.
- **Trade-off variants** spend traffic to buy quality. Their rank depends on the population, which is unavoidable under spread normalisation: they lose in P2 and gain in A and H, mostly from rapid motion, where the reference's 0.16 dB drop is visible.
  - `tradeoff_current_depth_refresh` is the paper's own "without deferred depth update" ablation. It re-reads current depths, costing 10.6 / 12.6 pp of traffic for near-exact order.
  - `*_hybrid*` refresh only high-churn tiles.
- **`weaker_fixed_boundaries`** (Algorithm 1 without interleaved boundaries) ties the reference: 0.0000–0.0004 dB and < 0.2 rank-error differences. In this setup, the insertion/deletion merge shifts every table position each frame, so fixed cuts do not pin entries to a chunk. The gym therefore cannot show the benefit of interleaving. Its P2 value of +0.88 comes from the two-attempt normalisation inflating sub-0.001 dB differences to ±2 sd. It is an honest alternative the test cannot tell apart, not a loophole.

The red-team report's variants were scored on the previous artifact-based gym, with different metrics, so they are not directly comparable:

- **Better current-depth fix:** H +1.283, A −0.087. Its counterpart here is `tradeoff_current_depth_refresh`.
- **Weaker no-partial-sort:** H −0.165, but **A +0.736**, the wrong direction. It now fails the gate.

On train, the variants rank in the same order (`hardening/results/audit_scores_train.json`): drift +0.139 / +0.475 / +1.040; extra pass, periodic and brute force all negative in every population.

## Shortcuts from REDTEAM.md: fix, before and after

"Before" scores are the red-team's Δrank H / A / P on the old gym. "After" is Δrank A / P2 of the closest expressible attempt on the final gym's hidden test. A failed run in the final gym scores −3.177 / −3.040.

| shortcut | before | fix | after |
|---|---|---|---|
| copy_sorted_input | +3.970 / +1.976 / +6.100 | Methods never receive ids or orders; the evaluator builds every table. Closest attempt `shortcut_regen_unsorted` takes the preprocessing table in its given order. | fails (10 dB drop) → −3.177 / −3.040 |
| zero_traffic | +3.392 / +2.371 / +3.000 | Traffic is counted by the evaluator from the operations it executes. Closest attempt `shortcut_noop` issues no operations. | fails → −3.177 / −3.040 |
| negative_traffic | +4.078 / +2.850 / +3.000 | Traffic is a non-negative count, so negative values cannot be expressed. | — |
| baseline_inflate | +1.557 / +1.328 / +1.820 | `full_sort` is built into the evaluator; a manifest named `full_sort` is ignored (the audit's `hardening/audit_policies/full_sort.json` appears under `ignored_manifests`). | baseline unchanged |
| ablation_inflate | +1.202 / +0.507 / +0.480 | The deferred-update comparison is computed by the evaluator and is a diagnostic only. | — |
| omit_scenes / empty_scenes | +2.421 / +1.533 / +6.100 and −13.4 / −0.845 / +1.460 | The evaluator runs every scene for every manifest. A crash, exit or missing scene fails the whole run with worst values. Closest attempt `shortcut_skip_rapid_experiment` exits mid-scene. | fails → −3.177 / −3.040 |
| workload_shrink | +4.214 / +2.184 / +6.100 | Scenes are generated inside `eval/train` and `eval/test`. Hidden seeds exist only in `eval/test/evaluate.py`. | — |
| score_file_forge | 0 (tie) | A forged perfect `scores_test.json` planted before the official run is overwritten (`hardening/results/forge_check.txt`). | overwritten |
| unregistered_method / skip_bad_experiment | 0 / +0.172 / +0.265 / +0.390 | Every manifest in `policies/` is scored in both experiments. Invalid manifests and runs failing either experiment get worst values everywhere (`shortcut_malformed_manifest`, `shortcut_skip_rapid_experiment`). | fails → −3.177 / −3.040 |
| null_traffic / empty_orders | evaluator crashed, no score | Protocol errors fail only that method, with worst values (`shortcut_garbage_output`, `shortcut_oversized_window`). | fails → −3.177 / −3.040 |

### New shortcuts found and fixed this iteration

- **Abort the whole evaluation** (`shortcut_crash_evaluator`). The method answers with deeply nested JSON. Before the fix, `json.loads` raised `RecursionError`, which escaped the per-method error handling and aborted the entire hidden test. No scores were written for anyone, so a losing method was skipped instead of ranked low. This was replayed in the job against the pre-fix evaluator: `hardening/results/crash_before.log` shows exit code 1, scores written: no.
  - **Fix:** any exception that a method's response triggers now fails that method only.
  - **After:** worst values, −3.177 / −3.040. The reference is still scored.
- **Stall the evaluation** (`shortcut_stall`). Before the fix, a method could answer correctly but just under the 120 s per-response timeout, for 30 frames × 8 scenes. Whether that kills the job depends on the node:
  - a node exposing 8 cores (as here, scenes in parallel) would take about 1 h;
  - a node exposing one core would take about 8 h, past the 6 h job limit, leaving no scores at all.

  This "before" is from analysis; I did not replay it, since that would have burned hours of job time.
  - **Fix:** a method may spend at most 600 s answering over one scene. The reference needs milliseconds.
  - **After:** fails at frame 7, −3.177 / −3.040.
- **Brute force outranking the reference in small populations.** In this iteration's protocol with the old coefficients, the exact full re-sort and the built-in baseline outranked the reference by +0.500 in P2. The two quality coefficients summed to 1.25, more than the traffic coefficient of 1.0. Fixed by the coefficient change below; now −0.960.

### Shortcuts left, and why

- **Reading `eval/test/` or the evaluator process from inside a policy.** At test time a policy runs as the same user on the same filesystem, so it could read the hidden seeds and privately simulate each scene to pick per-tile operations. No file permission can stop this inside one container. `scoring/CONSTRAINTS.md` forbids it, and the separate grader checks for it.

  Without that leak, a method cannot compute the objective on hidden instances. The protocol sends only per-tile counts, per-block inversion counts and an affine depth fit, never Gaussian data. So the public generator and renderer in `eval/train/` give no private search on the test.
- **Leftover processes** that rewrite score files after the evaluator exits. Out of scope: the hidden test runs as its own job in a fresh container.
- **Trading quality within the limit.** Example: inserting new Gaussians lazily on low-churn tiles while staying under 0.1 dB. This is allowed, and its quality loss is measured and penalised. `tradeoff_alternate_frame_insertion`, which defers insertion every other frame, exceeds the limit (0.127 dB) and fails.
- **Population dependence of trade-offs.** Pareto-better and Pareto-worse results rank correctly in every population. Trade-offs (more traffic for better quality) rank above or below the reference depending on the population's spread. That is inherent to spread-normalised ranks, not a loophole.
- **Synthetic generator knowledge.** The scene generator is public in `eval/train/`. A method could train on unlimited generated scenes; that is ordinary learning, and the test is the same family. It cannot "write down" the hidden scenes, because it never observes them.

## Reference score, before and after

| | before (red-team, old gym, test) | after (final gym, test) | after (train) |
|---|---|---|---|
| normal motion | 50.56% traffic saved; adjacent-order accuracy 0.656; no image quality measured | **68.01%** traffic saved, **0.0184 dB** PSNR drop, rank error 9.63 | 68.31%, 0.0169 dB, 11.48 |
| rapid motion (2× camera speed) | — | **43.49%**, **0.1594 dB**, 22.81 | 46.01%, 0.1780 dB, 23.71 |

- **Traffic:** sorting-stage traffic falls from 1605.9 MB to 513.7 MB under normal motion and from 1482.6 MB to 837.9 MB under rapid motion.
- **Deferred depth update:** the same run without the deferred update would need 855.6 / 1213.7 MB. That is a 39.96% / 30.97% saving from the deferred update, against the paper's 33.2–35.8%.
- **Quality:** the paper reports ≤ 0.1 dB (mean 0.067 dB). The reference stays well under the 0.1 dB limit under normal motion and visibly degrades under rapid motion. That is the direction of the paper's own caveat ("Gaussian reusability decreases under rapid camera motion").
- **Train and test agree:** within 0.3 pp (normal motion) and 2.5 pp (rapid motion).
- **Cost:** the hidden test of the reference plus the baseline takes about 7 min on one core, with no training.

## Headroom

- **No metric is at its bound.** The reference reaches the bound of no scored metric: traffic 68.0% / 43.5% (bound 100), PSNR drop 0.018 / 0.159 dB (bound 0), rank error 9.6 / 22.8 (bound 0).
- **Where the paper falls short.** `rapid_camera_motion` was added earlier in this iteration from the paper's own rapid-movement study (Fig. 17b). It sits where the paper's method falls short: 0.16 dB is above the 0.1 dB the paper calls imperceptible.
- **A variant beats the reference.** The drift-compensated variant beats it at equal traffic. It cuts the PSNR drop by 70% under rapid motion (0.159 → 0.048 dB) and by 21% under normal motion, and still sits far from every bound (43.5% traffic, 0.048 dB, 7.9 rank error).
- **Brute force does not pay.** The exact full re-sort solves ordering perfectly but saves no traffic, the paper's primary benefit. It ranks below the reference in every population.
- **The baseline is clearly below the reference.** `full_sort` scores 0% vs 68% / 43% saved, on a scale with ample room above the reference.

## Coefficient and weight changes

Experiment weights are unchanged (0.6 normal motion, 0.4 rapid motion).

| | traffic_reduction_pct | psnr_drop_db | mean_abs_rank_error |
|---|---|---|---|
| before | 1.0 / 1.0 | 1.0 / 1.0 | 0.25 / 0.25 |
| after | 1.0 / 1.0 | **0.3 / 0.6** | **0.1 / 0.1** |

Values are normal / rapid motion. Why:

- **Traffic outweighs the quality terms combined.** The paper's claim is "less traffic without visible quality loss": traffic is the benefit, and quality is a constraint already gated at 0.1 / 1.0 dB. Making the traffic coefficient exceed the sum of the quality coefficients in each experiment guarantees that a method saving no traffic cannot outrank the reference by being exact, even in a two-attempt normalisation.
- **Quality counts more under rapid motion.** The reference's quality loss is imperceptible under normal motion and visible under rapid motion, so the PSNR drop weighs 0.6 there against 0.3.
- **Rank error is a minor diagnostic.** The paper does not report it, so it only diagnoses ordering fidelity.

Failed runs now receive each experiment's quality limit (0.1 / 1.0 dB) as their PSNR drop, instead of 10 dB. Any run above the limit fails, so the limit is the worst value a scored run can have; failed runs are still dominated on every metric. The 10 dB value made the population spread of PSNR drop about 100× larger than the differences between passing methods. In population A that made quality gains count for almost nothing (drift +0.019 → +0.078 now).

Only failed entries depend on this rule, so the saved audit outputs were rescored with `hardening/rescore_failed.py` rather than re-run. The official `scoring/scores_{train,test}.json` contain no failed method and are unchanged by it.

## Departures from the paper that remain

These were not fixable within this iteration's budget and are stated plainly:

- **Synthetic scenes, not trained 3DGS scenes.**
  - Scenes are procedurally generated street-like Gaussian scenes, with 768×448 images, 64-px tiles and about 2000–2400 entries per tile, rather than trained Tanks-and-Temples 3DGS models at QHD.
  - 30 scored frames per scene instead of 60. The metrics are traffic ratios and mean quality, so frame count enters only through the dynamics.
  - The camera speed is calibrated to the paper's tile-retention statistics (Fig. 6/7).
- **An analytic traffic model, not measured DRAM traffic.** Traffic is an analytic table-entry model of the sorting stage (8-byte entries), not cycle-accurate DRAM traffic of the whole pipeline. The paper's 81.3% is end-to-end versus GSCore; it stays in `scoring/reference.json` as context, not as a value to match.
- **PSNR drop against exact order, not photos.** Quality is the PSNR drop from blending sampled pixels in the method's order instead of exact order, expressed at the paper's mean reconstruction PSNR. There is no comparison against ground-truth photos and no LPIPS.
- **Hardware claims are untested.** Throughput, area and power are outside this gym.
- **Interleaving cannot be distinguished.** The interleaved chunk boundaries of Algorithm 1 are implemented as in the paper, but their benefit cannot be measured here (see `weaker_fixed_boundaries`).
- **Rapid-motion reference values are measured, not paper values.** For `rapid_camera_motion`, `scoring/reference.json` holds the measured reference (labelled as such), because the paper reports only throughput there.

The reproduced method follows the paper's steps and settings: 256-entry chunks, interleaved boundaries, a single off-chip pass with insertion and valid-bit deletion in the merge, and the deferred depth update. There was no earlier simplification of it to restore.

## Files

- `hardening/audit_policies/`: manifests of the reference, the variants, brute force and the shortcuts.
- `hardening/variant_policy.py`: their protocol implementations.
- `hardening/rank_report.py`: the A / H / P2 ranks.
- `hardening/rescore_failed.py`: applies the failure rule to saved outputs.
- `hardening/results/`:
  - job logs and the audit scores and diagnostics (test, and train subset);
  - rank tables, final and before the fix (`audit_rank_test*.txt`, `audit_rank_test.json`);
  - `forge_check.txt` and `crash_before.log`.
- `scripts/run.sh` reproduces the reference end to end: train, then test, then `validate.py`.
