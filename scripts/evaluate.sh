#!/bin/bash
# Standard evaluation entry point: scores every registered method
# (policies/<name>.json) plus the built-in full_sort baseline on the visible
# scenes and writes scoring/scores.json (same content as scores_train.json).
#
#   bash scripts/evaluate.sh [policy_dir]
#
# Uses only code in eval/; methods are run as separate processes through the
# documented stdin/stdout protocol (see briefing/evaluation.md), never imported.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

POLICY_DIR="${1:-policies}"
python3 eval/train/evaluate.py --policy-dir "$POLICY_DIR" --output scoring/scores.json
