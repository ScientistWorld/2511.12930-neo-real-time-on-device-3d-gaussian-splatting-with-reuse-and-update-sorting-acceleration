#!/bin/bash
# Hardening check job (iteration 11). Runs inside the gym container, no internet.
#
#  1. Official reference runs: every manifest in policies/ (the paper's method)
#     plus the built-in full_sort baseline, train and hidden test, via the
#     no-argument scripts. A forged scores_test.json is planted first to show
#     that the hidden test overwrites it.
#  2. Audit: the reference, better/weaker variants, brute force and shortcuts
#     (hardening/audit_policies/) through the unchanged hidden-test and train
#     evaluators, all paired on the same scenes.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

mkdir -p hardening/results
echo "cpus: $(nproc)" | tee hardening/results/job_info.txt
python3 --version | tee -a hardening/results/job_info.txt

# ---- 1. official reference runs ------------------------------------------
bash scripts/evaluate_train.sh 2>&1 | tee hardening/results/official_train.log
cp scoring/scores_train.json scoring/scores.json
cp scoring/diagnostics_train.json scoring/diagnostics.json

python3 - <<'EOF'
import json
forged = {"experiments": {e: {"results": {"neo_reuse_update": {
    "traffic_reduction_pct": 100.0, "psnr_drop_db": 0.0, "mean_abs_rank_error": 0.0}}}}
    for e in ("synthetic_temporal_sorting", "rapid_camera_motion")}}
open("scoring/scores_test.json", "w").write(json.dumps(forged))
EOF
bash scripts/evaluate_test.sh 2>&1 | tee hardening/results/official_test.log
python3 - <<'EOF' | tee hardening/results/forge_check.txt
import json
s = json.load(open("scoring/scores_test.json"))
v = s["experiments"]["synthetic_temporal_sorting"]["results"]["neo_reuse_update"]["traffic_reduction_pct"]
print("forged value overwritten:", v != 100.0, "(traffic_reduction_pct =", v, ")")
EOF

# ---- 2. audit population through the hidden test and train ---------------
python3 eval/test/evaluate.py --policy-dir hardening/audit_policies \
  --output hardening/results/audit_scores_test.json --log-dir outputs/eval_logs/audit_test \
  2>&1 | tee hardening/results/audit_test.log
python3 eval/train/evaluate.py --policy-dir hardening/audit_policies \
  --output hardening/results/audit_scores_train.json --log-dir outputs/eval_logs/audit_train \
  2>&1 | tee hardening/results/audit_train.log

python3 hardening/rank.py hardening/results/audit_scores_test.json | tee hardening/results/audit_rank_test.txt
python3 validate.py --compare 2>&1 | tee hardening/results/validate.log || true
