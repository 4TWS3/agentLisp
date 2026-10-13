"""契约 CT-DECOMPOSITION-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

import logging

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_decomposition_behavior() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "decomposition", "max-depth": 2}]
    from runtime.patterns import load

    load(h)
    dd = h.patterns.api("decomposition")
    assert dd.children("t", 2) == ["t.1", "t.2"]
    try:
        dd.children("t", 3)
        raise AssertionError("超过 max-depth 应报错")
    except ValueError:
        logging.getLogger(__name__).debug("swallowed exception", exc_info=True)
    assert "pattern:decomposition" in str(h.build_context()), "CT-DECOMPOSITION-01：上下文应含指令"


def test_decomposition_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:decomposition" not in str(h.build_context())
