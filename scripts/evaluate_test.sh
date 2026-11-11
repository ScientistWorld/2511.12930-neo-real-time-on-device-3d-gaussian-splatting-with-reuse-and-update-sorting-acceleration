#!/bin/bash
# Score every method registered in policies/ on the hidden test scenes.
#
#   bash scripts/evaluate_test.sh [policy_dir] [scores_output]
#
# With no arguments every manifest policies/<name>.json is run through the
# sorting-engine protocol of eval/test/evaluate.py (same interface as the
# train evaluator, held-out scenes generated inside eval/test/), together
# with the built-in full_sort baseline. Scores go to scoring/scores_test.json.
# Nothing a method writes is read back: all numbers are recomputed here.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

POLICY_DIR="${1:-policies}"
SCORES_OUTPUT="${2:-scoring/scores_test.json}"

python3 eval/test/evaluate.py --policy-dir "$POLICY_DIR" --output "$SCORES_OUTPUT"
