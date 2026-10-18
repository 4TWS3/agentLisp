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


def test_reducers_accumulate_instead_of_overwrite() -> None:
    """:state 声明了 :reducer 的字段要累积；没声明的才覆盖。"""
    wf = _wf(("a", "agent"), ("b", "agent"), edges=[("a", "b")])
    fields = {
        "chapters": {"type": "dict", "reducer": "merge"},
        "log": {"type": "list", "reducer": "append"},
        "total": {"type": "int", "reducer": "sum"},
        "last": {"type": "str"},
    }
    app = build_graph(
        wf,
        {
            "a": lambda s: {"chapters": {"ch1": "x"}, "log": ["a"], "total": 1, "last": "a"},
            "b": lambda s: {"chapters": {"ch2": "y"}, "log": ["b"], "total": 2, "last": "b"},
        },
        state_fields=fields,
    )
    out = app.invoke({})
    assert out["chapters"] == {"ch1": "x", "ch2": "y"}, out
    assert out["log"] == ["a", "b"], out
    assert out["total"] == 3, out
    assert out["last"] == "b", "没有 reducer 的字段应覆盖"


def test_unknown_reducer_is_loud() -> None:
    with pytest.raises(WorkflowBridgeError) as exc:
        build_graph(
            _wf(("a", "agent"), edges=[]),
            {"a": lambda s: {}},
            state_fields={"x": {"type": "dict", "reducer": "nope"}},
        )
    assert "nope" in str(exc.value)


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


def test_conditional_loop_repeats_until_predicate_says_done() -> None:
    """conditional-loop：跑完最后一个节点后问 <首个>__while 要不要再来一轮。"""
    import asyncio

    runs: list[str] = []
    wf = {
        "entry": "write",
        "nodes": [
            {"name": "write", "type": "agent", "handler": None, "output_fields": ["draft"]},
            {"name": "check", "type": "evaluator", "handler": None, "output_fields": ["ok"]},
            {"name": "publish", "type": "agent", "handler": None, "output_fields": ["final"]},
        ],
        "edges": [
            {"from": "write", "to": "check", "kind": "edge"},
            {"from": "check", "to": "publish", "kind": "edge"},
        ],
        "loops": [{"nodes": ["write", "check"], "while": "need_retry", "max_rounds": 0}],
    }
    app = build_graph(
        wf,
        {
            "write": lambda s: (runs.append("write"), {"draft": "v"})[1],
            "check": lambda s: (runs.append("check"), {"ok": True})[1],
            "publish": lambda s: (runs.append("publish"), {"final": "done"})[1],
            # 前两轮判定「还要改」，第三轮通过
            "write__while": lambda s: len([r for r in runs if r == "write"]) < 3,
        },
    )
    out = asyncio.run(app.ainvoke({}))
    assert runs == ["write", "check", "write", "check", "write", "check", "publish"], runs
    assert out["final"] == "done"


def test_conditional_loop_respects_max_rounds() -> None:
    """max_rounds 到顶就 done，不看判定函数。"""
    import asyncio

    runs: list[str] = []
    wf = {
        "entry": "w",
        "nodes": [
            {"name": "w", "type": "agent", "handler": None, "output_fields": ["n"]},
            {"name": "c", "type": "evaluator", "handler": None, "output_fields": []},
            {"name": "z", "type": "agent", "handler": None, "output_fields": []},
        ],
        "edges": [
            {"from": "w", "to": "c", "kind": "edge"},
            {"from": "c", "to": "z", "kind": "edge"},
        ],
        "loops": [{"nodes": ["w", "c"], "while": "always", "max_rounds": 2}],
    }
    app = build_graph(
        wf,
        {
            "w": lambda s: (runs.append("w"), {"n": 1})[1],
            "c": lambda s: (runs.append("c"), {})[1],
            "z": lambda s: (runs.append("z"), {})[1],
            "w__while": lambda s: True,  # 永远想再来一轮
        },
    )
    asyncio.run(app.ainvoke({}))
    assert runs.count("w") == 2, runs
    assert runs[-1] == "z"


def test_conditional_loop_without_predicate_is_loud() -> None:
    wf = {
        "entry": "a",
        "nodes": [
            {"name": "a", "type": "agent", "handler": None, "output_fields": []},
            {"name": "b", "type": "agent", "handler": None, "output_fields": []},
        ],
        "edges": [{"from": "a", "to": "b", "kind": "edge"}],
        "loops": [{"nodes": ["a", "b"], "while": "x", "max_rounds": 0}],
    }
    with pytest.raises(WorkflowBridgeError) as exc:
        build_graph(wf, {"a": lambda s: {}, "b": lambda s: {}})
    assert "a__while" in str(exc.value)


def test_subagent_nodes_route_to_named_agents() -> None:
    """多 agent 编排：subagent 节点按 :handler 里的 agent 名路由到不同 harness。"""
    calls: list[str] = []

    class _FakeHarness:
        def __init__(self, name: str) -> None:
            self.name = name

        async def run(self, _prompt: str):
            calls.append(self.name)

            class _T:
                final_answer = f"{self.name} 的产出"

            return _T()

    wf = {
        "entry": "a",
        "nodes": [
            {"name": "a", "type": "subagent", "handler": "tianji", "output_fields": ["judge"]},
            {"name": "b", "type": "subagent", "handler": "yaoguang", "output_fields": ["report"]},
        ],
        "edges": [{"from": "a", "to": "b", "kind": "edge"}],
    }
    import asyncio

    app = build_graph(
        wf,
        {},
        agents={
            "tianji": lambda: _FakeHarness("tianji"),
            "yaoguang": lambda: _FakeHarness("yaoguang"),
        },
    )
    out = asyncio.run(app.ainvoke({}))
    assert calls == ["tianji", "yaoguang"], calls
    assert out["judge"] == "tianji 的产出"
    assert out["report"] == "yaoguang 的产出"


def test_subagent_with_unknown_agent_is_loud() -> None:
    wf = {
        "entry": "a",
        "nodes": [{"name": "a", "type": "subagent", "handler": "nope", "output_fields": []}],
        "edges": [],
    }
    with pytest.raises(WorkflowBridgeError) as exc:
        build_graph(wf, {}, agents={"tianji": object})
    assert "nope" in str(exc.value)


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
