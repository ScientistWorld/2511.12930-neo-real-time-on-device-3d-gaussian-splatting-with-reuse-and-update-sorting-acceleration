#!/bin/bash
set -euo pipefail
AUDIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python "$AUDIT_DIR/harness.py" shortcut_skip_bad_experiment
