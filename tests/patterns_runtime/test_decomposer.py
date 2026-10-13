"""契约 CT-DECOMPOSER-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_decomposer_behavior() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "decomposer", "schema-fields": ["name", "kind"]}]
    from runtime.patterns import load

    load(h)
    dc = h.patterns.api("decomposer")
    ok, bad = dc.validate_payload({"name": "a"})
    assert not ok and bad == ["kind"]
    assert "pattern:decomposer" in str(h.build_context()), "CT-DECOMPOSER-01：上下文应含指令"


def test_decomposer_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:decomposer" not in str(h.build_context())
