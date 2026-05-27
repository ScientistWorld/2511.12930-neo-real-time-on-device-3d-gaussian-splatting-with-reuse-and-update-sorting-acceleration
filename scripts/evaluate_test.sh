#!/bin/bash
# Evaluate the held-out test slice of the Neo sorting gym.
#
# Mirrors scripts/evaluate.sh argument shape:
#   ./scripts/evaluate_test.sh [candidate_output] [baseline_output] [scores_output]
#
# With no candidate_output, this scores the same method entries found in
# scoring/scores_train.json when that file exists; otherwise it discovers every
# compatible artifact under outputs/. The output is always scores_test.json by
# default and the Python path is eval/test/.

set -e

cd /home/user

mkdir -p scoring

CANDIDATE_OUTPUT="${1:-}"
BASELINE_OUTPUT="${2:-}"
SCORES_OUTPUT="${3:-scoring/scores_test.json}"
TRAIN_SCORES="${TRAIN_SCORES:-scoring/scores_train.json}"

ARGS=(--output "$SCORES_OUTPUT")
if [[ -n "$CANDIDATE_OUTPUT" ]]; then
  ARGS+=(--candidate "$CANDIDATE_OUTPUT")
elif [[ -f "$TRAIN_SCORES" ]]; then
  ARGS+=(--methods-from-train "$TRAIN_SCORES")
fi
if [[ -n "$BASELINE_OUTPUT" ]]; then
  ARGS+=(--baseline "$BASELINE_OUTPUT")
fi

python eval/test/evaluate.py "${ARGS[@]}"
