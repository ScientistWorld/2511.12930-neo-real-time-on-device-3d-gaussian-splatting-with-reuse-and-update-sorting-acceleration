#!/bin/bash
# Evaluate the visible train slice of the Neo sorting gym.
#
# Mirrors scripts/evaluate.sh argument shape:
#   ./scripts/evaluate_train.sh [candidate_output] [baseline_output] [scores_output]
#
# With no candidate_output, every compatible artifact under outputs/ is
# discovered and scored. This keeps the evaluator method-agnostic for future
# variants while preserving the original artifact interface.

set -e

cd /home/user

mkdir -p scoring

CANDIDATE_OUTPUT="${1:-}"
BASELINE_OUTPUT="${2:-}"
SCORES_OUTPUT="${3:-scoring/scores_train.json}"

ARGS=(--output "$SCORES_OUTPUT")
if [[ -n "$CANDIDATE_OUTPUT" ]]; then
  ARGS+=(--candidate "$CANDIDATE_OUTPUT")
fi
if [[ -n "$BASELINE_OUTPUT" ]]; then
  ARGS+=(--baseline "$BASELINE_OUTPUT")
fi

python eval/train/evaluate.py "${ARGS[@]}"
