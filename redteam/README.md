Audit candidates run in isolated copies of exactly the visible interface. Each
folder's `run.sh` prepares and executes its candidate and then invokes the
restored, unmodified hidden test as `bash scripts/evaluate_test.sh`, with no
arguments. See `harness.py` for the copy list and restoration boundary.
`candidate.py` contains each explicitly named shortcut; honest modified source
is stored in the corresponding variant folder. `source/` preserves the original
improve-mode method and baseline for reproducibility. Candidate code never reads
the paper, hidden evaluator, reference coefficients, or hidden scores.

Run `bash redteam/run_all.sh` inside the gym container to reproduce all cases.
Individual `run.sh` files reproduce one case. Computation belongs on job nodes.
Scores and compact status files are retained in every run folder; runtime copies
and reusable trained/generated artifacts are ignored by `redteam/.gitignore`.

Rank values use the supplied directions, absolute coefficient magnitudes, and
experiment weights. Since future attempts determine each metric's normalization,
`summarize.py` reports three explicit populations, including a reference-versus-
candidate two-attempt population. The actual anchor is the reproduced hidden-test
reference, not the paper-scale numbers in `scoring/reference.json`.
