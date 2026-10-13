"""契约 CT-EXPLORATION-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_exploration_behavior() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "exploration", "budget": 3, "convergence": 0.01}]
    from runtime.patterns import load

    load(h)
    ex = h.patterns.api("exploration")
    assert ex.should_stop(3, 0.5) is True
    assert ex.should_stop(1, 0.001) is True
    assert ex.should_stop(1, 0.5) is False
    assert "pattern:exploration" in str(h.build_context()), "CT-EXPLORATION-01：上下文应含指令"


def test_exploration_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:exploration" not in str(h.build_context())
