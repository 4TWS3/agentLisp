#!/usr/bin/env python3
"""_tmp_bracket_diff.py: diagnostic that counts square/paren balance per line.

Used by CI temp workflow to diagnose missing `]` / `)` / mismatches on a
per-file basis. Prints a running depth and flags any line where depth goes
negative (malformation) plus the final balance totals.
"""
from __future__ import annotations

import sys


def diff_file(path: str) -> int:
    sq = par = 0
    first_neg_sq: tuple[int, int, str] | None = None
    first_neg_par: tuple[int, int, str] | None = None

    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            for c in line:
                if c == '[':
                    sq += 1
                elif c == ']':
                    sq -= 1
                    if sq < 0 and first_neg_sq is None:
                        first_neg_sq = (i, sq, line.rstrip()[:120])
                elif c == '(':
                    par += 1
                elif c == ')':
                    par -= 1
                    if par < 0 and first_neg_par is None:
                        first_neg_par = (i, par, line.rstrip()[:120])

    print(f"{path}: final bracket balance  sq={sq} par={par}")
    if first_neg_sq:
        ln, depth, txt = first_neg_sq
        print(f"{path}: FIRST NEGATIVE sq depth={depth} at L{ln}: {txt!r}")
    if first_neg_par:
        ln, depth, txt = first_neg_par
        print(f"{path}: FIRST NEGATIVE par depth={depth} at L{ln}: {txt!r}")
    return 0 if sq == 0 and par == 0 else 2


if __name__ == "__main__":
    rc = 0
    for p in sys.argv[1:]:
        rc |= diff_file(p)
    sys.exit(rc)
