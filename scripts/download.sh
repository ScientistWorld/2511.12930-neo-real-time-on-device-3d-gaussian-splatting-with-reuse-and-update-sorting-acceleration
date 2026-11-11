#!/bin/bash
# Download all data and models needed for this environment.
#
# Estimated total download size: 0 GB
# Estimated disk usage after extraction: 0 GB
#
# This gym needs no external data or model weights: the evaluators generate
# their Gaussian scenes and camera trajectories procedurally from fixed seeds
# (eval/train/ for the visible scenes, eval/test/ for the held-out ones), and
# everything runs on the Python standard library. The script is kept so the
# fresh-clone procedure is uniform; it only creates the local download folder.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

mkdir -p data/downloads
