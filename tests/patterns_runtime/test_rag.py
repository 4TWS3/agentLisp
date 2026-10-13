"""契约 CT-RAG-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_rag_behavior() -> None:
    """行为：带 :pattern rag → 确定性可观测行为 + 上下文指令。"""
    h = _harness()
    h.PATTERNS = [{"pattern": "rag"}]
    from runtime.patterns import load

    load(h)
    ok, why = h.patterns.api("rag").verify_evidence("见 [doc-7] 的结论", ["doc-7"])
    assert ok, why
    ok2, _ = h.patterns.api("rag").verify_evidence("没有引用", ["doc-7"])
    assert not ok2
    assert "pattern:rag" in str(h.build_context()), "CT-RAG-01：上下文应含指令"


def test_rag_counterproof() -> None:
    """反证：不带 :pattern → 无 handler、无指令。"""
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:rag" not in str(h.build_context())
