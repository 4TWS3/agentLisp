"""契约 CT-EVALUATOR-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_evaluator_behavior() -> None:
    """行为：带 :pattern evaluator → 确定性可观测行为 + 上下文指令。"""
    h = _harness()
    h.PATTERNS = [{"pattern": "evaluator", "thresholds": [0.4, 0.8]}]
    from runtime.patterns import load

    load(h)
    ev = h.patterns.api("evaluator")
    assert (ev.evaluate(0.9), ev.evaluate(0.5), ev.evaluate(0.1)) == ("pass", "rework", "escalate")
    assert "pattern:evaluator" in str(h.build_context()), "CT-EVALUATOR-01：上下文应含指令"


def test_evaluator_counterproof() -> None:
    """反证：不带 :pattern → 无 handler、无指令。"""
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:evaluator" not in str(h.build_context())
