"""生成回路评测：N 条需求 -> 一次通过率。

判据：pass_rate = 一次编译通过的需求数 / 总数。
这是「让模型写 .al」是否成立的唯一硬指标。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.al_generate import generate  # noqa: E402

EVAL = ROOT / "docs" / "llm" / "eval_set.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--limit", type=int, default=0, help="只跑前 N 条")
    ap.add_argument("-r", "--rounds", type=int, default=3)
    args = ap.parse_args()

    cases = [
        json.loads(line) for line in EVAL.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if args.limit:
        cases = cases[: args.limit]

    ok = 0
    rounds_total = 0
    for c in cases:
        src, rounds, _err = generate(c["req"], args.rounds)
        rounds_total += rounds
        if src:
            ok += 1
        print(f"{c['id']} {'PASS' if src else 'FAIL'} 轮数={rounds}", flush=True)

    n = len(cases)
    print(f"\n[eval] 通过 {ok}/{n} = {ok / n:.0%}  平均轮数 {rounds_total / n:.1f}")
    return 0 if ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
