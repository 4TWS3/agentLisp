"""契约 CT-PRIORITY-01 的运行时测试（行为 1 条 + 反证 1 条）。

契约：docs/spec/pattern_runtime_contracts/priority.md（id = CT-PRIORITY-01）
"""

from __future__ import annotations

from typing import Any

from runtime.base_harness_v2 import BaseHarnessV2

CANDIDATES = [
    {"id": "a", "urgency": 1},
    {"id": "b", "urgency": 3},
    {"id": "c", "urgency": 2},
]


def _harness(**kwargs: Any) -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {}, **kwargs)


def test_CT_PRIORITY_01_behavior_order_and_context_directive() -> None:
    """行为：带 :pattern priority → order 降序 + 上下文出现确定性指令。"""
    h = _harness()
    h.PATTERNS = [{"pattern": "priority", "criteria": "urgency", "levels": 3}]
    from runtime.patterns import load

    load(h)

    assert [c["id"] for c in h.patterns.order(CANDIDATES)] == ["b", "c", "a"], (
        "CT-PRIORITY-01：应按 criteria=urgency 降序"
    )
    ctx_text = str(h.build_context())
    assert "pattern:priority" in ctx_text and "criteria=urgency" in ctx_text, (
        "CT-PRIORITY-01：build_context 应含 priority 指令"
    )
    assert h.patterns.landed() == ["priority"]


def test_CT_PRIORITY_01_counterproof_without_pattern_is_baseline() -> None:
    """反证：不带 :pattern → 无 handler、无指令、order 为原顺序（行为回基线）。"""
    h = _harness()
    assert getattr(h, "PATTERNS", None) in (None, []), "普通 harness 不应带 PATTERNS"
    assert h.patterns.handlers == [], "未声明模式不得载入 handler"
    assert h.patterns.order(CANDIDATES) == CANDIDATES, "反证：order 必须原样返回"
    assert "pattern:priority" not in str(h.build_context()), "反证：不得出现指令"
