"""契约 CT-PLANNER-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_planner_behavior() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "planner", "plan-size": 3}]
    from runtime.patterns import load

    load(h)
    pl = h.patterns.api("planner")
    assert pl.plan_size() == 3
    assert pl.completion(1, 4) == 0.25
    assert "pattern:planner" in str(h.build_context()), "CT-PLANNER-01：上下文应含指令"


def test_planner_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:planner" not in str(h.build_context())
