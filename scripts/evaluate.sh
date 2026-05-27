#!/bin/bash
# Evaluation script — the standard way to evaluate work in this environment.
#
# This script must be SELF-CONTAINED using only code in eval/.
# Do NOT import from method/ — evaluate.sh must work even when the
# paper's method code is hidden from a scientist agent.
#
# Design it so that anyone following the same output format can run
# this script to evaluate their results.
#
# OUTPUT CONTRACT: This script MUST write scoring/scores.json containing
# a JSON dict nested by experiment, e.g.:
#   {"imagenet_classification": {"top1_accuracy": 82.1, "top5_accuracy": 94.8}}
# Experiment and metric names must match the keys in scoring/reference.json.
# This file is read by the system for automated comparison.
#
# Example usage:
#   ./evaluate.sh                                      # discover artifacts in outputs/
#   ./evaluate.sh outputs/candidate.json               # evaluate one candidate plus baseline
#   ./evaluate.sh outputs/candidate.json outputs/full_sort.json scoring/scores.json
#
# Called from run.sh after training, or independently.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

mkdir -p scoring

METHOD_OUTPUT="${1:-}"
BASELINE_OUTPUT="${2:-}"
SCORES_OUTPUT="${3:-scoring/scores.json}"

ARGS=(--output "$SCORES_OUTPUT" --outputs-dir outputs)
if [ -n "$METHOD_OUTPUT" ]; then
  ARGS+=(--candidate "$METHOD_OUTPUT")
fi
if [ -n "$BASELINE_OUTPUT" ]; then
  ARGS+=(--baseline "$BASELINE_OUTPUT")
fi

python eval/evaluate_sorting.py "${ARGS[@]}"
