"""契约 CT-HITL-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_hitl_behavior() -> None:
    """行为：带 :pattern hitl → 确定性可观测行为 + 上下文指令。"""
    h = _harness()
    h.PATTERNS = [{"pattern": "hitl", "approval-before": ["deploy", "git-push"]}]
    from runtime.patterns import load

    load(h)
    hh = h.patterns.api("hitl")
    assert hh.requires_approval("deploy") and not hh.requires_approval("read")
    assert "pattern:hitl" in str(h.build_context()), "CT-HITL-01：上下文应含指令"


def test_hitl_counterproof() -> None:
    """反证：不带 :pattern → 无 handler、无指令。"""
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:hitl" not in str(h.build_context())
