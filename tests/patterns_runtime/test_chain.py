"""契约 CT-CHAIN-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_chain_behavior() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "chain", "steps": ["plan", "act"]}]
    from runtime.patterns import load

    load(h)
    cc = h.patterns.api("chain")
    assert cc.steps() == ["plan", "act"]
    assert cc.next_step(1) == "act" and cc.next_step(2) is None
    assert "pattern:chain" in str(h.build_context()), "CT-CHAIN-01：上下文应含指令"


def test_chain_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:chain" not in str(h.build_context())
