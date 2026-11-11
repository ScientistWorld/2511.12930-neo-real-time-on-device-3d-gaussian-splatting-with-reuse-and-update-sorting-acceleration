#!/bin/bash
# Hardening check job (iteration 11). Runs inside the gym container, no internet.
#
#  1. Official reference runs from the final code: every manifest in policies/
#     (the paper's method) plus the built-in full_sort baseline, train and
#     hidden test, through the no-argument scripts. A forged scores_test.json
#     is planted first to show that the hidden test overwrites it.
#  2. Before/after for the evaluator-abort shortcut: the pre-fix test
#     evaluator (git revision 43eb1c3) and the fixed one on the same policy.
#  3. Audit: the reference, better/weaker variants, brute force and shortcuts
#     (hardening/audit_policies/) through the unchanged hidden-test evaluator,
#     and the honest variants through the train evaluator, all paired on the
#     same scenes.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

R=hardening/results
mkdir -p "$R"
{ echo "cpus: $(nproc)"; python3 --version; date -u; } | tee "$R/job_info.txt"

# ---- 1. official reference runs ------------------------------------------
bash scripts/evaluate_train.sh 2>&1 | tee "$R/official_train.log"
cp scoring/scores_train.json scoring/scores.json
cp scoring/diagnostics_train.json scoring/diagnostics.json

python3 - <<'EOF'
import json
exps = ("synthetic_temporal_sorting", "rapid_camera_motion")
perfect = {"traffic_reduction_pct": 100.0, "psnr_drop_db": 0.0, "mean_abs_rank_error": 0.0}
forged = {"experiments": {e: {"results": {"neo_reuse_update": dict(perfect)}} for e in exps}}
with open("scoring/scores_test.json", "w") as f:
    json.dump(forged, f)
EOF
bash scripts/evaluate_test.sh 2>&1 | tee "$R/official_test.log"
python3 - <<'EOF' | tee "$R/forge_check.txt"
import json
s = json.load(open("scoring/scores_test.json"))
v = s["experiments"]["synthetic_temporal_sorting"]["results"]["neo_reuse_update"]["traffic_reduction_pct"]
print("forged value overwritten:", v != 100.0, "(traffic_reduction_pct =", v, ")")
EOF
date -u | tee -a "$R/job_info.txt"

# ---- 2. evaluator-abort shortcut, before and after the fix -----------------
mkdir -p tmp/crash_pol
cp policies/neo_reuse_update.json hardening/audit_policies/shortcut_crash_evaluator.json tmp/crash_pol/
if git show 43eb1c3:eval/test/evaluate.py > eval/test/_before_fix.py 2>/dev/null; then
  set +e
  python3 eval/test/_before_fix.py --policy-dir tmp/crash_pol --output tmp/crash_before/scores.json \
    --log-dir tmp/crash_before/logs > "$R/crash_before.log" 2>&1
  echo "exit code: $?" >> "$R/crash_before.log"
  set -e
  if [ -f tmp/crash_before/scores.json ]; then echo "scores written: yes" >> "$R/crash_before.log"; \
  else echo "scores written: no" >> "$R/crash_before.log"; fi
  tail -5 "$R/crash_before.log"
else
  echo "git unavailable; before-fix replay skipped" | tee "$R/crash_before.log"
fi
rm -f eval/test/_before_fix.py

# ---- 3. audit population through the hidden test and train ---------------
python3 eval/test/evaluate.py --policy-dir hardening/audit_policies \
  --output "$R/audit_scores_test.json" --log-dir outputs/eval_logs/audit_test \
  2>&1 | tee "$R/audit_test.log"
date -u | tee -a "$R/job_info.txt"

rm -rf tmp/audit_train_pol && mkdir -p tmp/audit_train_pol
for n in neo_reuse_update better_drift_compensated better_drift_compensated_hybrid \
         brute_force_exact_full_sort tradeoff_current_depth_refresh tradeoff_hybrid_refresh \
         weaker_extra_pass weaker_fixed_boundaries weaker_no_partial_sort weaker_periodic_full_sort; do
  cp "hardening/audit_policies/$n.json" tmp/audit_train_pol/
done
python3 eval/train/evaluate.py --policy-dir tmp/audit_train_pol \
  --output "$R/audit_scores_train.json" --log-dir outputs/eval_logs/audit_train \
  2>&1 | tee "$R/audit_train.log"
date -u | tee -a "$R/job_info.txt"

python3 hardening/rank.py "$R/audit_scores_test.json" | tee "$R/audit_rank_test.txt"
python3 validate.py --compare 2>&1 | tee "$R/validate.log" || true
