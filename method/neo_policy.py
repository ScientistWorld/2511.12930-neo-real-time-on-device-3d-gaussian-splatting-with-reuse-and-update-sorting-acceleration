#!/usr/bin/env python3
"""Neo reuse-and-update sorting policy (Oh et al., ASPLOS'26, Sec. 4 and 5.3).

Each frame and tile, the previous frame's Gaussian table is reused and updated
in a single off-chip pass (Sec. 4.3 "Single off-chip sorting pass"):

  1. Reordering with Dynamic Partial Sorting (Algorithm 1): the table is read
     in chunks of at most C = 256 entries that are sorted on chip.  Chunk
     boundaries are interleaved between frames: odd frames use [0,C), [C,2C),
     ...; even frames shift every boundary by C/2 so entries can cross the
     previous frame's boundaries (Fig. 9b).
  2. Insertion: the newly visible (incoming) Gaussians, sorted on chip, are
     merged into the reordered stream by the merge unit (MSU+).
  3. Deletion: entries whose valid bit was cleared by the previous frame's
     rasterization are dropped during the same merge.
  4. Depth update: deferred to rasterization (Sec. 4.4); the sorting stage
     never pays for a separate depth-refresh pass.

The memory machine that executes these hardware operations and counts their
DRAM traffic is part of the evaluator; this file only decides which operations
the sorting engine performs.
"""

from __future__ import annotations

import argparse
import json
import sys


def dynamic_partial_sort_cuts(frame: int, length: int, chunk: int) -> list[int]:
    """Chunk boundaries of Algorithm 1 for one table of `length` entries."""
    first = chunk if frame % 2 == 1 else chunk // 2
    return list(range(first, length, chunk))


def tile_ops(frame: int, info: dict, chunk: int) -> list[dict]:
    length = int(info["L"])
    return [{
        "op": "pass",
        "start": 0,
        "end": length,
        "cuts": dynamic_partial_sort_cuts(frame, length, chunk),
        "sort": True,
        "merge": True,
    }]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk", type=int, default=0,
                        help="Chunk size; 0 uses the on-chip capacity announced by the evaluator (256).")
    args = parser.parse_args()
    chunk = args.chunk
    for line in sys.stdin:
        msg = json.loads(line)
        kind = msg.get("type")
        if kind == "scene":
            capacity = int(msg["capacity"])
            chunk = min(args.chunk, capacity) if args.chunk > 0 else capacity
        elif kind == "frame":
            frame = int(msg["frame"])
            ops = [tile_ops(frame, info, chunk) for info in msg["tiles"]]
            sys.stdout.write(json.dumps({"ops": ops}, separators=(",", ":")) + "\n")
            sys.stdout.flush()
        elif kind == "end":
            break


if __name__ == "__main__":
    main()
