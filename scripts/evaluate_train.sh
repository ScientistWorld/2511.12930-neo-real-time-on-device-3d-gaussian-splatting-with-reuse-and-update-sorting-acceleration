#!/bin/bash
# Score every method registered in policies/ on the visible train scenes.
#
#   bash scripts/evaluate_train.sh [policy_dir] [scores_output]
#
# With no arguments every manifest policies/<name>.json is run through the
# sorting-engine protocol of eval/train/evaluate.py, together with the
# evaluator's built-in full_sort baseline, and the scores are written to
# scoring/scores_train.json (per-scene diagnostics: scoring/diagnostics_train.json).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

POLICY_DIR="${1:-policies}"
SCORES_OUTPUT="${2:-scoring/scores_train.json}"

python3 eval/train/evaluate.py --policy-dir "$POLICY_DIR" --output "$SCORES_OUTPUT"
