#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user

mkdir -p data outputs

if [ ! -e data/neo_synthetic_workload.json ]; then
  python data/synthetic_workload.py --output data/neo_synthetic_workload.json
fi

python method/neo_sort.py \
  --workload data/neo_synthetic_workload.json \
  --output outputs/neo_reuse_update.json

if [ ! -e outputs/full_sort.json ]; then
  bash scripts/baseline.sh
fi

bash scripts/evaluate.sh
