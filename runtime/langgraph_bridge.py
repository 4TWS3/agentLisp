"""把编译产物里的 `self.WORKFLOW` 变成 LangGraph 图。

为什么需要这个桥：agentLisp 的 `:workflow` 只负责**声明**（编译器校验并发射 WORKFLOW 字典），
执行交给 LangGraph。分工是：
  - LangGraph：图、中断、恢复、checkpoint
  - agentLisp：节点内的 agent（护栏 / 工具 / trace / 模式）

用法：
    from runtime.langgraph_bridge import build_graph
    wf = MyHarness.WORKFLOW
    app = build_graph(wf, {"facts": my_facts, "judge": run_agent_node})
    out = app.invoke({"messages": []})

节点实现从哪来（按顺序找）：
    1. handlers[节点名]
    2. handlers[节点声明的 :handler 字符串]
    3. 自动 import 该 :handler 字符串
    4. 都没有 -> 报错，并点名哪个节点缺实现
"""

from __future__ import annotations

import importlib
import inspect
import itertools
from collections.abc import Callable
from typing import Any

NodeFn = Callable[[dict[str, Any]], dict[str, Any]]

# state 字段的累积语义（与编译器 STATE-REDUCER-ENUM 一一对应）。
# 没有 reducer 的字段就是覆盖——这是最容易丢数据的地方，所以显式声明。
REDUCERS: dict[str, Callable[[Any, Any], Any]] = {
    "merge": lambda old, new: {**(old or {}), **(new or {})},
    "append": lambda old, new: [*(old or []), *(new or [])],
    "sum": lambda old, new: (old or 0) + (new or 0),
}


class WorkflowBridgeError(RuntimeError):
    """图与实现对不上（缺节点实现、边引用非法等）。"""


def _import_handler(path: str) -> NodeFn:
    """ ":handler" 形如 "module.func" 或 "module.Class.method"。"""
    parts = path.split(".")
    for split in range(len(parts) - 1, 0, -1):
        mod_name = ".".join(parts[:split])
        try:
            obj: Any = importlib.import_module(mod_name)
        except ImportError:
            continue
        for attr in parts[split:]:
            obj = getattr(obj, attr)
        return obj  # type: ignore[no-any-return]
    raise WorkflowBridgeError(f"无法解析 :handler {path!r}（模块导不进来或属性不存在）")


def _make_subagent(node: dict[str, Any], agents: dict[str, Any]) -> NodeFn:
    """subagent 节点：按 :handler 里的 agent 注册名，起对应 harness 跑一轮。"""
    agent_name = node.get("handler") or node["name"]
    cls = agents.get(agent_name)
    if cls is None:
        raise WorkflowBridgeError(
            f"subagent 节点 {node['name']!r} 指向 agent {agent_name!r}，"
            f"但 agents 里没有它；已注册 {sorted(agents)}"
        )
    static = str(node.get("static") or "")
    dynamic = str(node.get("dynamic") or "")

    async def run(state: dict[str, Any]) -> dict[str, Any]:
        import json

        payload = {
            k: v
            for k, v in state.items()
            if k not in {"messages", "chapters"} and not k.startswith("_")
        }
        # :dynamic 段里的 {字段} 用当前 state 展开（F-AMS-5 的插值）
        import re as _re

        def _sub(m: Any) -> str:
            key = str(m.group(1))
            v = state.get(key)
            return json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)

        dyn = _re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", _sub, dynamic)
        task = (static + ("\n\n" + dyn if dyn else "")).strip() or f"完成子任务：{node['name']}"
        h = cls()
        trace = await h.run(task + "\n\n当前已知：\n" + json.dumps(payload, ensure_ascii=False))
        answer = str(getattr(trace, "final_answer", "") or "")
        outs = list(node.get("output_fields") or [])
        return {k: answer for k in outs} if outs else {"result": answer}

    return run


def _resolve(
    node: dict[str, Any],
    handlers: dict[str, NodeFn],
    agents: dict[str, Any] | None = None,
) -> NodeFn:
    name = node["name"]
    if name in handlers:
        return handlers[name]
    handler = node.get("handler")
    if handler and handler in handlers:
        return handlers[handler]
    if node.get("type") == "subagent":
        return _make_subagent(node, agents or {})
    if handler:
        return _import_handler(handler)
    raise WorkflowBridgeError(
        f"节点 {name!r}（type={node.get('type')}）没有实现："
        f"请把它放进 handlers['{name}']，或在 :handler 里声明 模块.函数"
    )


def _with_round_counter(fn: Callable[..., Any], key: str) -> Callable[..., Any]:
    """给 loop 的首个节点套一层计数，供 max_rounds 判定。"""

    async def run(state: dict[str, Any]) -> dict[str, Any]:
        n = int(state.get(key, 0)) + 1
        result = fn({**state, key: n})
        if inspect.isawaitable(result):
            result = await result
        return {**result, key: n}

    return run


def _loop_predicate(pred: Callable[[dict[str, Any]], Any], key: str, max_rounds: int):
    """把 :while 判定包装成 LangGraph 的条件边函数（again / done）。"""

    def route(state: dict[str, Any]) -> str:
        if max_rounds and int(state.get(key, 0)) >= max_rounds:
            return "done"
        return "again" if pred(state) else "done"

    return route


def _node_fn(
    node: dict[str, Any],
    handlers: dict[str, NodeFn],
    reducers: dict[str, Callable[[Any, Any], Any]] | None = None,
    agents: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    impl = _resolve(node, handlers, agents)
    name = node["name"]
    outputs = list(node.get("output_fields") or [])
    field_reducers = reducers or {}

    def _merge(state: dict[str, Any], result: Any) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise WorkflowBridgeError(
                f"节点 {name!r} 必须返回 dict（状态增量），得到 {type(result).__name__}"
            )
        delta = {k: result[k] for k in outputs if k in result} if outputs else result
        merged = {**state, **delta}
        # 声明了 reducer 的字段走累积，不覆盖（chapters / trace_log / total 这类）。
        for key, fn in field_reducers.items():
            if key in result:
                merged[key] = fn(state.get(key), result[key])
        return merged

    if inspect.iscoroutinefunction(impl) or inspect.isasyncgenfunction(impl):

        async def run_async(state: dict[str, Any]) -> dict[str, Any]:
            result = impl(state)
            if inspect.isawaitable(result):
                result = await result
            return _merge(state, result)

        run_async.__name__ = name
        return run_async

    def run(state: dict[str, Any]) -> dict[str, Any]:
        result = impl(state)
        if inspect.isawaitable(result):
            raise WorkflowBridgeError(
                f"节点 {name!r} 返回了 awaitable，但不是 async def；"
                "请把它写成 async def，这样 LangGraph 才会 await 它"
            )
        return _merge(state, result)

    run.__name__ = name
    return run


def build_graph(
    workflow: dict[str, Any],
    handlers: dict[str, NodeFn],
    *,
    state_schema: Any = None,
    checkpointer: Any = None,
    state_fields: dict[str, Any] | None = None,
    agents: dict[str, Any] | None = None,
    entry_router: Callable[[dict[str, Any]], str] | None = None,
) -> Any:
    """按 WORKFLOW 建 LangGraph 应用。

    workflow：编译产物的 `self.WORKFLOW`
    handlers：节点实现（节点名 或 :handler 字符串 -> 可调用）
    """
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover
        raise WorkflowBridgeError(
            "需要 langgraph：pip install 'langgraph>=0.2'（本桥不内置图引擎）"
        ) from exc

    nodes = workflow.get("nodes") or []
    if not nodes:
        raise WorkflowBridgeError("WORKFLOW 没有节点")
    entry = workflow.get("entry")
    known = {n["name"] for n in nodes}
    if entry not in known:
        raise WorkflowBridgeError(f":entry {entry!r} 不是已声明节点")

    # 从 :state 的 :reducer 声明里取累积规则（编译产物里的 STATE_FIELDS）
    field_reducers: dict[str, Callable[[Any, Any], Any]] = {}
    for fname, fspec in (state_fields or {}).items():
        red = (fspec or {}).get("reducer") if isinstance(fspec, dict) else None
        if red:
            if red not in REDUCERS:
                raise WorkflowBridgeError(
                    f"state 字段 {fname!r} 的 :reducer {red!r} 未实现；已支持 {sorted(REDUCERS)}"
                )
            field_reducers[fname] = REDUCERS[red]

    edges = workflow.get("edges") or []
    plain = [e for e in edges if e.get("kind", "edge") == "edge"]
    conditional = [e for e in edges if e.get("kind") == "conditional-edge"]
    loops = workflow.get("loops") or []

    # ---- conditional-loop：编译器给出 (nodes, while, max_rounds)，桥负责接成条件边 ----
    # 语义：跑完 loop 的最后一个节点后，问 "<首个节点>__while" 要不要再跑一轮。
    loop_plans: list[dict[str, Any]] = []
    skip_from: set[str] = set()
    for lp in loops:
        ns = [str(x) for x in (lp.get("nodes") or [])]
        if not ns:
            raise WorkflowBridgeError("conditional-loop 的 :nodes 为空")
        for x in ns:
            if x not in known:
                raise WorkflowBridgeError(f"conditional-loop 引用不存在的节点 {x!r}")
        first, last = ns[0], ns[-1]
        pred = handlers.get(first + "__while") or handlers.get(str(lp.get("while", "")))
        if pred is None:
            raise WorkflowBridgeError(
                f"conditional-loop（{first}→{last}）缺判定函数："
                f"请提供 handlers['{first}__while'] 或 handlers[{lp.get('while')!r}]"
            )
        nxt = next((e["to"] for e in plain if e["from"] == last), None)
        loop_plans.append(
            {
                "first": first,
                "last": last,
                "pred": pred,
                "next": nxt,
                "max_rounds": int(lp.get("max_rounds") or 0),
                "key": "_loop_rounds_" + first,
            }
        )
        skip_from.add(last)

    g = StateGraph(state_schema if state_schema is not None else dict)
    wrap_first = {p["first"]: p for p in loop_plans}
    for n in nodes:
        fn = _node_fn(n, handlers, field_reducers, agents)
        plan = wrap_first.get(n["name"])
        if plan is not None:
            fn = _with_round_counter(fn, plan["key"])
        g.add_node(n["name"], fn)

    for e in plain:
        for end in (e["from"], e["to"]):
            if end not in known:
                raise WorkflowBridgeError(f"边引用了不存在的节点 {end!r}")
        if e["from"] in skip_from:
            # 这一条被 conditional-loop 接管（again / done 二选一）
            continue
        g.add_edge(e["from"], e["to"])

    # 编译器在**校验**可达性时会合成环内边（loop-pairs），但**没有发射**它们。
    # 桥必须自己补，否则 loop 的第二个及之后的节点运行时不可达（实测：整段循环被静默跳过）。
    existing = {(e["from"], e["to"]) for e in plain}
    for lp in loops:
        ns = [str(x) for x in (lp.get("nodes") or [])]
        for a, b in itertools.pairwise(ns):
            if (a, b) not in existing:
                g.add_edge(a, b)
                existing.add((a, b))

    for plan in loop_plans:
        g.add_conditional_edges(
            plan["last"],
            _loop_predicate(plan["pred"], plan["key"], plan["max_rounds"]),
            {"again": plan["first"], "done": plan["next"] or END},
        )

    # 条件边：同一源的多条条件边共用一个路由函数 handlers["<源>__route"]
    by_src: dict[str, list[str]] = {}
    for e in conditional:
        by_src.setdefault(e["from"], []).append(e["to"])
    for src, targets in by_src.items():
        router = handlers.get(src + "__route")
        if router is None:
            raise WorkflowBridgeError(
                f"{src!r} 有 {len(targets)} 条 conditional-edge，但缺路由函数 handlers['{src}__route']"
            )
        # 条件是可以指向 END 的（实测 tianxuan 有 {"clarify_prepare": ..., "END": END}）
        g.add_conditional_edges(src, router, {t: (END if t == "END" else t) for t in targets})

    # 入口本身可以是条件路由（tianxuan 的 route_after_start）
    if entry_router is not None:
        g.add_conditional_edges(START, entry_router, {**{n: n for n in known}, "END": END})
    else:
        g.add_edge(START, entry)

    # 终端节点（没有出边）连到 END
    has_out = {e["from"] for e in edges}
    for n in nodes:
        if n["name"] not in has_out:
            g.add_edge(n["name"], END)

    return g.compile(checkpointer=checkpointer) if checkpointer is not None else g.compile()
