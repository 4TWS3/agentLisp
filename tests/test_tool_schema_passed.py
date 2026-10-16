"""US-29 前置：harness 必须把工具 schema 传给 provider。

原因：provider 不拿到 tools，就不会产出 tool_calls -> 真工具路径断。
本测试用可捕获 provider 证明 harness 真的传了。
"""

from __future__ import annotations

import asyncio
from typing import Any

from runtime.base_harness_v2 import BaseHarnessV2


class _Recorder:
    name = "openai"

    def __init__(self) -> None:
        self.tools_seen: list[Any] = []
        self.calls = 0

    async def achat(
        self, messages: list[dict[str, Any]], tools: Any = None, **kwargs: Any
    ) -> dict[str, Any]:
        self.tools_seen.append(tools)
        self.calls += 1
        if self.calls == 1:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "tc1",
                        "type": "function",
                        "function": {"name": "noop", "arguments": {}},
                    }
                ],
            }
        return {"role": "assistant", "content": "done", "tool_calls": None}


class _Registry:
    def __init__(self) -> None:
        self.called: list[str] = []

    def names(self) -> list[str]:
        return ["noop"]

    def to_openai_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "noop",
                    "description": "no-op",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

    async def acall(self, name: str, **kwargs: Any) -> dict[str, Any]:
        self.called.append(name)
        return {"exit_code": 0, "stdout": "ok", "stderr": ""}


def test_harness_passes_tool_schema_to_provider() -> None:
    llm = _Recorder()
    reg = _Registry()
    h = BaseHarnessV2({}, {}, {}, {}, llm_client=llm, tool_registry=reg)
    asyncio.run(h.run("do it"))
    assert llm.tools_seen, "provider 从未被调用"
    assert llm.tools_seen[0], "harness 未把工具 schema 传给 provider（真工具路径断）"
    assert reg.called == ["noop"], "tool_calls 未被执行"
