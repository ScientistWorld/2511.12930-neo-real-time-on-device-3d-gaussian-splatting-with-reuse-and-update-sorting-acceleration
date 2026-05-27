#!/bin/bash
# Download all data and models needed for this environment.
#
# Run on a node with internet access BEFORE building the container
# or submitting compute jobs.
#
# This script should be idempotent — safe to run multiple times.
# It should skip files that already exist.
#
# Update the storage estimate below as you add downloads.
#
# Estimated total download size: 0 GB
# Estimated disk usage after extraction: <0.1 GB
#
# You do not need to run this script during reproduction because the benchmark
# uses deterministic generated data. It exists for future portability and keeps
# all workspace-local paths explicit.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

mkdir -p data/downloads

# No external data or model downloads are required. The benchmark workload is
# generated deterministically by data/synthetic_workload.py.
