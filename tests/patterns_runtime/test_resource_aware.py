"""契约 CT-RESOURCE_AWARE-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_resource_aware_behavior() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "resource-aware", "budget": "low"}]
    from runtime.patterns import load

    load(h)
    ra = h.patterns.api("resource-aware")
    assert ra.tier() == "small"
    assert "pattern:resource-aware" in str(h.build_context()), (
        "CT-RESOURCE_AWARE-01：上下文应含指令"
    )


def test_resource_aware_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:resource-aware" not in str(h.build_context())
