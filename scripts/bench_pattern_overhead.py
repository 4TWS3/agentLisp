#!/usr/bin/env python3
"""US-40 / US-41：模式接入开销与长跑稳定（非阻塞验收，P4.1a）。

US-40 判据：每轮 handler < 1 ms（经验值）。
US-41 判据：1000 轮不退化（经验值；后 100 轮均值 <= 前 100 轮 * 1.2 + 0.05ms）。

退出码：0 = 两条都过；1 = 不过。
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.base_harness_v2 import BaseHarnessV2  # noqa: E402
from runtime.patterns import load  # noqa: E402

PATTERNS = [
    {"pattern": "priority", "criteria": "urgency", "levels": 3},
    {"pattern": "exception", "retries": 2, "backoff": "linear"},
    {"pattern": "exploration", "budget": 3, "convergence": 0.1},
]
ROUNDS = 1000
THRESHOLD_MS = 1.0


def _harness() -> BaseHarnessV2:
    h = BaseHarnessV2({}, {}, {}, {})
    h.PATTERNS = [dict(p) for p in PATTERNS]
    load(h)
    return h


def _one_round(h: BaseHarnessV2) -> float:
    """一轮 = 三个 hook 各走一遍。返回毫秒。"""
    ctx = {"messages": []}
    t0 = time.perf_counter()
    h.patterns.before_turn(ctx)
    h.patterns.on_tool_call({"tool_name": "bash", "args": {}})
    h.patterns.verify_observation({"answer": "x", "evidence_ids": ["x"]})
    return (time.perf_counter() - t0) * 1000.0


def main() -> int:
    h = _harness()
    times = [_one_round(h) for _ in range(ROUNDS)]
    avg = statistics.mean(times)
    p99 = sorted(times)[max(0, int(len(times) * 0.99) - 1)]
    first = statistics.mean(times[:100])
    last = statistics.mean(times[-100:])
    ratio = last / first if first > 0 else float("inf")
    print("轮数=" + str(len(times)))
    print("平均每轮 " + f"{avg:.4f}" + " ms（阈值 < " + str(THRESHOLD_MS) + " ms）")
    print("p99 " + f"{p99:.4f}" + " ms")
    print(
        "前 100 轮均值 "
        + f"{first:.4f}"
        + " ms / 后 100 轮均值 "
        + f"{last:.4f}"
        + " ms（退化比 "
        + f"{ratio:.3f}"
        + "）"
    )
    ok_overhead = avg < THRESHOLD_MS
    ok_stability = last <= first * 1.2 + 0.05
    print("OK" if (ok_overhead and ok_stability) else "FAIL")
    return 0 if (ok_overhead and ok_stability) else 1


if __name__ == "__main__":
    raise SystemExit(main())
