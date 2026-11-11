#!/usr/bin/env python3
"""Exact per-frame full re-sort expressed through the sorting-engine protocol.

Every frame the preprocessing stage rewrites each tile table from scratch
(regen), the engine sorts 256-entry chunks on chip and then merges the sorted
runs with two-way merge passes.  This is the conventional sorting the paper
compares against; the evaluator scores the same procedure as its fixed built-in
``full_sort`` baseline, so this file is only a reference implementation of the
brute-force strategy (it is not registered in policies/).
"""

from __future__ import annotations

import json
import sys


def full_sort_ops(n: int, chunk: int, fanin: int) -> list[dict]:
    ops: list[dict] = [{"op": "regen"}]
    if n == 0:
        return ops
    cuts = list(range(chunk, n, chunk))
    ops.append({"op": "pass", "start": 0, "end": n, "cuts": cuts})
    runs = [0] + cuts + [n]
    while len(runs) > 2:
        next_runs = [0]
        for g in range(0, len(runs) - 1, fanin):
            group = runs[g:g + fanin + 1]
            if len(group) > 2:
                ops.append({"op": "merge_runs", "start": group[0], "end": group[-1], "cuts": group[1:-1]})
            next_runs.append(group[-1])
        runs = next_runs
    return ops


def main() -> None:
    chunk, fanin = 256, 2
    for line in sys.stdin:
        msg = json.loads(line)
        if msg.get("type") == "scene":
            chunk, fanin = int(msg["capacity"]), int(msg["merge_fanin"])
        elif msg.get("type") == "frame":
            ops = [full_sort_ops(int(info["N"]), chunk, fanin) for info in msg["tiles"]]
            sys.stdout.write(json.dumps({"ops": ops}, separators=(",", ":")) + "\n")
            sys.stdout.flush()
        elif msg.get("type") == "end":
            break


if __name__ == "__main__":
    main()
