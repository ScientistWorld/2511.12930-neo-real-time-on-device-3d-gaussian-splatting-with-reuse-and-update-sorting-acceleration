#!/bin/bash
# Run the paper's proposed method (Neo reuse-and-update sorting).
#
# The method is the sorting-engine policy method/neo_policy.py, registered by
# policies/neo_reuse_update.json. It needs no training: the evaluator runs it
# frame by frame on every scene, so "running the method" means scoring it.
#
#   bash scripts/method.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

test -f policies/neo_reuse_update.json
bash scripts/evaluate.sh
