"""契约 CT-PARALLEL-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_parallel_behavior() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "parallel", "branches": ["a", "b"]}]
    from runtime.patterns import load

    load(h)
    pp = h.patterns.api("parallel")
    assert pp.fan_in([1, 2]) == [1, 2]
    assert pp.branches() == ["a", "b"]
    assert "pattern:parallel" in str(h.build_context()), "CT-PARALLEL-01：上下文应含指令"


def test_parallel_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:parallel" not in str(h.build_context())
