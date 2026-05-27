# Verification Report

## Initial Assessment

The workspace entered final verification at `core_claim_plus`. The milestone is justified for the scaled sorting reproduction: the paper's reuse-and-update sorting flow runs end to end, a full-sort baseline is present, the evaluator reads artifacts rather than method code, and train/test scoring artifacts are present and validated.

## Issues Found

- **Minor:** `scripts/evaluate.sh` and `eval/evaluate_sorting.py` still used method-specific default names for the official score path, making the public evaluator less reusable for future candidate artifacts.
- **Minor:** Several method-agnostic documentation files described the component ablation using implementation-specific wording.
- **Minor:** The component-ablation score weighted absolute traffic saved, which could reward larger workloads. The scale-normalized savings percentage better matches the gym objective.
- **Cosmetic/known:** Root `README.md`, `manifest.json`, and `trajectory/` status entries are system bind-mount or runtime artifacts outside the reproducible workspace path.

## Fixes Applied

- Updated `scripts/evaluate.sh` and `eval/evaluate_sorting.py` so the official evaluator discovers compatible artifacts under `outputs/` and accepts a generic `--candidate` path while preserving backward compatibility.
- Tightened `briefing/evaluation.md`, `scoring/EXPERIMENTS.md`, `scoring/TARGETS.md`, and `scoring/CONSTRAINTS.md` to describe the task and experiments at a method-safe level.
- Updated `scoring/reference.json` so `deferred_update_savings_pct` is the primary weighted component-ablation metric and `deferred_update_savings_MB` is diagnostic only.
- Reran `bash scripts/reproduce.sh` and `python validate.py --compare`; validation passed.

## Final Judgment

The workspace is ready to serve as a research gym for the reproduced claim. Improve-mode agents can modify the method and use the same artifact-based evaluator, while from-scratch agents can understand the problem and scoring without importing the paper method. The main limitation is scope: this gym covers the sorting/traffic claim on deterministic synthetic per-tile traces, not full rendered-scene PSNR/LPIPS or hardware cycle simulation.

- Milestone: core_claim_plus
- Ready for gym use: yes
- Confidence: medium
- Key limitation: synthetic per-tile sorting traces replace unreleased trained 3DGS scenes and hardware simulation.
