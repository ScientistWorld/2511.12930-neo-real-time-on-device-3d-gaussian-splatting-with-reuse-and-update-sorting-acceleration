#!/bin/bash
set -euo pipefail
cd /home/user
bash redteam/shortcut_skip_bad_experiment/run.sh
python redteam/summarize.py
