#!/bin/bash
# Reproduce the reference end to end inside the gym container (no internet).
#
# The paper's method (policies/neo_reuse_update.json -> method/neo_policy.py)
# needs no training. Every registered method and the evaluator's built-in
# full_sort baseline are scored on the visible train scenes
# (scoring/scores_train.json, mirrored to scoring/scores.json) and on the
# held-out test scenes (scoring/scores_test.json); then the workspace is
# validated. About 15 minutes on one CPU core.
#
# The iteration-11 hardening audit (variants, brute force and shortcuts through
# the same evaluators) is documented in HARDENING.md; its manifests are in
# hardening/audit_policies/ and can be scored with
#   python3 eval/test/evaluate.py --policy-dir hardening/audit_policies --output <file>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

bash scripts/reproduce.sh
