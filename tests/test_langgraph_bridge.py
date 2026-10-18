"""agentLisp 的 :workflow 交给 LangGraph 执行（runtime/langgraph_bridge.py）。

判据：
  - 线性图按序执行，state 逐节点累积
  - 缺实现 / 返回非 dict / 边引用非法 -> 明确报错并点名
  - :handler "模块.函数" 能自动解析
  - 条件边用 handlers["<源>__route"] 路由
"""

from __future__ import annotations

import sys
import types

import pytest

pytest.importorskip("langgraph", reason="未装 langgraph（本桥不内置图引擎）")

from runtime.langgraph_bridge import WorkflowBridgeError, build_graph


def _wf(*nodes: tuple[str, str], edges: list[tuple[str, str]], entry: str = "") -> dict:
    return {
        "entry": entry or nodes[0][0],
        "nodes": [{"name": n, "type": t, "handler": None, "output_fields": []} for n, t in nodes],
        "edges": [{"from": a, "to": b, "kind": "edge"} for a, b in edges],
    }


def test_linear_runs_in_order_and_merges_state() -> None:
    seen: list[str] = []
    app = build_graph(
        _wf(("a", "computation"), ("b", "agent"), ("c", "agent"), edges=[("a", "b"), ("b", "c")]),
        {
            "a": lambda s: (seen.append("a"), {"x": 1})[1],
            "b": lambda s: (seen.append("b"), {"y": s["x"] + 1})[1],
            "c": lambda s: (seen.append("c"), {"z": s["y"] + 1})[1],
        },
    )
    out = app.invoke({})
    assert seen == ["a", "b", "c"]
    assert out == {"x": 1, "y": 2, "z": 3}, "state 必须逐节点累积"


def test_async_node_is_awaited() -> None:
    """agent 节点通常是 async（要跑 agentLisp harness），LangGraph 必须 await 它。"""
    import asyncio

    async def a(state: dict) -> dict:
        await asyncio.sleep(0)
        return {"x": 1}

    async def b(state: dict) -> dict:
        await asyncio.sleep(0)
        return {"y": state["x"] + 1}

    app = build_graph(_wf(("a", "agent"), ("b", "agent"), edges=[("a", "b")]), {"a": a, "b": b})
    assert asyncio.run(app.ainvoke({})) == {"x": 1, "y": 2}


def test_missing_implementation_names_the_node() -> None:
    app_nodes = _wf(("a", "computation"), ("b", "agent"), edges=[("a", "b")])
    with pytest.raises(WorkflowBridgeError) as exc:
        build_graph(app_nodes, {"a": lambda s: {}})
    assert "'b'" in str(exc.value)


def test_non_dict_return_is_rejected() -> None:
    app = build_graph(_wf(("a", "agent"), edges=[]), {"a": lambda s: 42})
    with pytest.raises(WorkflowBridgeError) as exc:
        app.invoke({})
    assert "必须返回 dict" in str(exc.value)


def test_handler_string_is_imported(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = types.ModuleType("_bridge_demo")
    mod.facts = lambda s: {"n": 7}  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "_bridge_demo", mod)
    wf = {
        "entry": "a",
        "nodes": [{"name": "a", "type": "computation", "handler": "_bridge_demo.facts"}],
        "edges": [],
    }
    assert build_graph(wf, {}).invoke({}) == {"n": 7}


def test_output_fields_limit_the_delta() -> None:
    wf = {
        "entry": "a",
        "nodes": [
            {"name": "a", "type": "agent", "handler": None, "output_fields": ["keep"]},
        ],
        "edges": [],
    }
    out = build_graph(wf, {"a": lambda s: {"keep": 1, "drop": 2}}).invoke({"seed": 0})
    assert out == {"seed": 0, "keep": 1}, out


def test_conditional_edge_uses_route_handler() -> None:
    wf = {
        "entry": "start",
        "nodes": [
            {"name": "start", "type": "agent", "handler": None},
            {"name": "yes", "type": "agent", "handler": None},
            {"name": "no", "type": "agent", "handler": None},
        ],
        "edges": [
            {"from": "start", "to": "yes", "kind": "conditional-edge"},
            {"from": "start", "to": "no", "kind": "conditional-edge"},
        ],
    }
    app = build_graph(
        wf,
        {
            "start": lambda s: {"go": False},
            "start__route": lambda s: "yes" if s.get("go") else "no",
            "yes": lambda s: {"branch": "yes"},
            "no": lambda s: {"branch": "no"},
        },
    )
    assert app.invoke({})["branch"] == "no"


def test_conditional_edge_without_router_is_loud() -> None:
    wf = {
        "entry": "s",
        "nodes": [
            {"name": "s", "type": "agent", "handler": None},
            {"name": "t", "type": "agent", "handler": None},
        ],
        "edges": [{"from": "s", "to": "t", "kind": "conditional-edge"}],
    }
    with pytest.raises(WorkflowBridgeError) as exc:
        build_graph(wf, {"s": lambda s: {}, "t": lambda s: {}})
    assert "s__route" in str(exc.value)
