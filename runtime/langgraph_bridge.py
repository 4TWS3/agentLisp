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
from collections.abc import Callable
from typing import Any

NodeFn = Callable[[dict[str, Any]], dict[str, Any]]


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


def _resolve(node: dict[str, Any], handlers: dict[str, NodeFn]) -> NodeFn:
    name = node["name"]
    if name in handlers:
        return handlers[name]
    handler = node.get("handler")
    if handler and handler in handlers:
        return handlers[handler]
    if handler:
        return _import_handler(handler)
    raise WorkflowBridgeError(
        f"节点 {name!r}（type={node.get('type')}）没有实现："
        f"请把它放进 handlers['{name}']，或在 :handler 里声明 模块.函数"
    )


def _node_fn(node: dict[str, Any], handlers: dict[str, NodeFn]) -> Callable[..., Any]:
    impl = _resolve(node, handlers)
    name = node["name"]
    outputs = list(node.get("output_fields") or [])

    def _merge(state: dict[str, Any], result: Any) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise WorkflowBridgeError(
                f"节点 {name!r} 必须返回 dict（状态增量），得到 {type(result).__name__}"
            )
        delta = {k: result[k] for k in outputs if k in result} if outputs else result
        return {**state, **delta}

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

    g = StateGraph(state_schema if state_schema is not None else dict)
    for n in nodes:
        g.add_node(n["name"], _node_fn(n, handlers))

    edges = workflow.get("edges") or []
    plain = [e for e in edges if e.get("kind", "edge") == "edge"]
    conditional = [e for e in edges if e.get("kind") == "conditional-edge"]

    for e in plain:
        for end in (e["from"], e["to"]):
            if end not in known:
                raise WorkflowBridgeError(f"边引用了不存在的节点 {end!r}")
        g.add_edge(e["from"], e["to"])

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
        g.add_conditional_edges(src, router, {t: t for t in targets})

    g.add_edge(START, entry)

    # 终端节点（没有出边）连到 END
    has_out = {e["from"] for e in edges}
    for n in nodes:
        if n["name"] not in has_out:
            g.add_edge(n["name"], END)

    return g.compile(checkpointer=checkpointer) if checkpointer is not None else g.compile()
