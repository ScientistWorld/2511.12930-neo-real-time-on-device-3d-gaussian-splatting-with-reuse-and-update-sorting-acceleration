#!/bin/bash
# Reproduce the paper's results end to end (inside the container, no internet).
#
# The method needs no training. Every registered method (policies/) and the
# built-in full-sort baseline are run on the visible train scenes
# (scoring/scores_train.json, mirrored to scoring/scores.json) and on the
# held-out test scenes (scoring/scores_test.json), then the workspace is
# validated.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

bash scripts/evaluate_train.sh
cp scoring/scores_train.json scoring/scores.json
cp scoring/diagnostics_train.json scoring/diagnostics.json
bash scripts/evaluate_test.sh
python3 validate.py --compare
