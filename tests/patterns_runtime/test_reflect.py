"""契约 CT-REFLECT-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_reflect_behavior() -> None:
    """行为：带 :pattern reflect → 确定性可观测行为 + 上下文指令。"""
    h = _harness()
    h.PATTERNS = [{"pattern": "reflect", "reviewer-agent": "critic-1"}]
    from runtime.patterns import load

    load(h)
    assert h.patterns.api("reflect").config() == {"reviewer": "critic-1"}
    assert "pattern:reflect" in str(h.build_context()), "CT-REFLECT-01：上下文应含指令"


def test_reflect_counterproof() -> None:
    """反证：不带 :pattern → 无 handler、无指令。"""
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:reflect" not in str(h.build_context())
