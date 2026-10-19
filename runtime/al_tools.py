"""把 DSL 里写的工具体（define-tool ... :body）接进 agentLisp 运行时。

为什么需要它：BaseHarnessV2 只认 BuiltinToolRegistry；自定义工具必须有实现。
模型 B 让实现可以在 .al 里写，编译成 Python 函数，这里按声明的入参生成 schema 并分发。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

TYPE_MAP = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
}


class FunctionToolRegistry:
    """实现 ToolRegistryProtocol：names / to_openai_schema / acall。"""

    def __init__(
        self,
        tools_config: dict[str, Any],
        bodies: dict[str, Callable[..., Any]],
        fallback: Any = None,
    ) -> None:
        self._bodies = dict(bodies)
        self._fallback = fallback
        self._specs: dict[str, list[dict[str, str]]] = {}
        for t in tools_config.get("define_tools", []) or []:
            self._specs[t["name"]] = list(t.get("inputs") or [])

    def names(self) -> list[str]:
        inner = self._fallback.names() if self._fallback is not None else []
        return sorted(set(self._specs) | set(inner))

    def to_openai_schema(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for name, inputs in self._specs.items():
            props = {
                kv["name"]: {"type": TYPE_MAP.get(kv.get("type", "str"), "string")} for kv in inputs
            }
            out.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": f"{name}（在 .al 里用 define-tool :body 实现）",
                        "parameters": {
                            "type": "object",
                            "properties": props,
                            "required": [kv["name"] for kv in inputs],
                        },
                    },
                }
            )
        if self._fallback is not None:
            out.extend(self._fallback.to_openai_schema())
        return out

    async def acall(self, name: str, **kwargs: Any) -> Any:
        fn = self._bodies.get(name)
        if fn is not None:
            return fn(**kwargs)
        if self._fallback is not None:
            return await self._fallback.acall(name, **kwargs)
        raise KeyError(f"工具 {name!r} 没有实现：既不在 .al 的 :body 里，也不在内建工具里")


def from_harness(harness: Any) -> FunctionToolRegistry | None:
    """从产物实例取出工具体并组装注册表；没有就返回 None。"""
    bodies = getattr(harness, "TOOL_BODIES", None)
    if not bodies:
        return None
    from runtime.builtin_tools import BuiltinToolRegistry

    cfg = getattr(harness, "tools_config", None) or {}
    builtin = BuiltinToolRegistry.from_config(cfg)
    return FunctionToolRegistry(cfg, bodies, fallback=builtin)
