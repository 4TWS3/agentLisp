"""Tool registry + optional MCP bridge."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Optional

from .errors import FeatureNotInstalledError, ToolNotFoundError

HandlerFn = Callable[..., Awaitable[Any] | Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, HandlerFn] = {}

    def register(self, name: str, handler: HandlerFn, *, override: bool = False) -> None:
        if name in self._handlers and not override:
            raise KeyError(f"tool already registered: {name}")
        self._handlers[name] = handler

    def unregister(self, name: str) -> None:
        self._handlers.pop(name, None)

    def get(self, name: str) -> HandlerFn:
        h = self._handlers.get(name)
        if h is None:
            raise ToolNotFoundError(name)
        return h

    def has(self, name: str) -> bool:
        return name in self._handlers

    def names(self) -> list[str]:
        return sorted(self._handlers.keys())

    def handlers(self) -> dict[str, HandlerFn]:
        return dict(self._handlers)

    async def call(self, name: str, /, **kwargs: Any) -> Any:
        fn = self.get(name)
        if asyncio.iscoroutinefunction(fn):
            return await fn(**kwargs)
        return fn(**kwargs)


class MCPToolBridge:
    """Optional MCP client bridge. Requires `uv pip install 'agentlisp[mcp]'`.

    This is a thin skeleton: forward tool calls to a configured MCP client session.
    """

    def __init__(self, mcp_client: Optional[Any] = None) -> None:
        self.client = mcp_client
        if mcp_client is None:
            try:  # pragma: no cover - optional import smoke
                import mcp  # noqa: F401  # type: ignore[import-not-found]
            except ImportError as exc:
                raise FeatureNotInstalledError("MCP client SDK", "mcp") from exc

    def bind(self, registry: ToolRegistry) -> None:
        if self.client is None:
            return
        tools = getattr(self.client, "list_tools", None)
        if asyncio.iscoroutinefunction(tools):
            raise NotImplementedError(
                "MCP bind currently expects tool names to be registered via registry.register(); "
                "extend this method with an async init call in your app."
            )
