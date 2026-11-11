# Scientist Constraints

## Interface

A method is a program registered by `policies/<name>.json` (`{"command": [...]}`) that speaks the stdin/stdout protocol in `briefing/evaluation.md`. The evaluators in `eval/` generate the scenes, execute the operations, count traffic, render and score. Do not modify `eval/`, `scripts/evaluate_*.sh` or the hardware constants they define (256-entry on-chip capacity, two-way merge, 8-byte entries, operation costs); the test evaluator is replaced by a hidden copy with different scenes.

## Fixed comparison

The `full_sort` baseline, the scenes, the number of frames, the rendering model and the quality limits are fixed by the evaluator. A manifest named `full_sort` is ignored.

## Information

A method may use only what the protocol sends (tile counts and rasterizer feedback) and whatever it learns from the visible train scenes. Reading files under `eval/test/`, inspecting the evaluator process, or otherwise obtaining hidden depths, ids or scene seeds is not allowed.

## Quality

A run fails, and receives the worst value of every metric, if its rendering-quality loss exceeds 0.1 dB PSNR under normal motion or 1.0 dB under rapid motion, or if it breaks the protocol.

## Compliance Checklist

- [ ] Method registered under `policies/` and runs without network access
- [ ] Uses only protocol information and train-scene knowledge
- [ ] `eval/`, `scripts/evaluate_*.sh` and hardware constants unchanged
- [ ] Deterministic output for the same input
