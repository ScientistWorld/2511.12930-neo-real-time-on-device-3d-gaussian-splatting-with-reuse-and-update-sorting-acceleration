#!/bin/bash
# Baseline: exact full re-sort of every tile every frame on the same hardware
# model. It is built into the evaluators (fixed comparison partner, method
# name "full_sort") and scored in every evaluation run; baseline/full_sort_policy.py
# is the same procedure written as a protocol policy, for reference.
#
#   bash scripts/baseline.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

bash scripts/evaluate.sh
