"""M2 接线测试：证明模式 handler 的输出**真的被引擎消费**（不只是声明）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness(**kw: object) -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {}, **kw)


def test_priority_orders_tools_presented_to_model() -> None:
    """priority：criteria 排序真的改变 build_context 里的工具顺序。"""
    tools = [
        {"type": "function", "function": {"name": "a", "urgency": 1}},
        {"type": "function", "function": {"name": "b", "urgency": 3}},
        {"type": "function", "function": {"name": "c", "urgency": 2}},
    ]
    h = _harness()
    h.PATTERNS = [{"pattern": "priority", "criteria": "urgency", "levels": 3}]
    from runtime.patterns import load

    load(h)
    ordered = h.patterns.order(list(tools))
    assert [t["function"]["name"] for t in ordered] == ["b", "c", "a"], "应按 urgency 降序"


def test_hitl_blocks_tool_until_approved() -> None:
    """hitl：approval-before 命中的工具真的被 constrain 拦截；带 approved 才放行。"""
    h = _harness()
    h.PATTERNS = [{"pattern": "hitl", "approval-before": ["deploy"]}]
    from runtime.patterns import load

    load(h)
    ok, why = h.constrain({"tool_name": "deploy", "args": {}})
    assert not ok and "hitl" in why, f"应被 hitl 拦截；实际 ok={ok} why={why!r}"
    ok2, _ = h.constrain({"tool_name": "deploy", "args": {}, "approved": True})
    assert ok2, "带 approved=True 应放行"


def test_m2_wiring_counterproof_without_patterns_is_baseline() -> None:
    """反证：不带模式 → 工具顺序不变、constrain 不因模式拦截。"""
    h = _harness()
    tools = [{"type": "function", "function": {"name": "a", "urgency": 1}}]
    assert h.patterns.order(tools) == tools, "反证：order 应原样返回"
    ok, _ = h.constrain({"tool_name": "deploy", "args": {}})
    assert ok, "反证：未声明 hitl 时不得拦截"
