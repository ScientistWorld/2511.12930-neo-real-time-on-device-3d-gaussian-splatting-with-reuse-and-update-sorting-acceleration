#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

mkdir -p data outputs

if [ ! -e data/neo_synthetic_workload.json ]; then
  python data/synthetic_workload.py --output data/neo_synthetic_workload.json
fi

python method/neo_sort.py \
  --workload data/neo_synthetic_workload.json \
  --output outputs/neo_reuse_update.json

python method/neo_sort.py \
  --workload data/neo_synthetic_workload.json \
  --output outputs/neo_no_deferred_depth_update.json \
  --separate-depth-refresh

if [ ! -e outputs/full_sort.json ]; then
  bash scripts/baseline.sh
fi

bash scripts/evaluate.sh
