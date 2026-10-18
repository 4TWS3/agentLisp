"""工具结果消息的 content 必须是字符串。

真缺陷（2026-10-17 第一次跑真模型时暴露）：
  runtime/base_harness_v2 曾把 observation（dict）直接塞进 role="tool" 的 content。
  OpenAI 兼容端点（含 Ollama）会 400：invalid message content type: map[string]interface {}。
  为什么此前没被发现：MockLLMClient 不出 tool_calls，测试从没走第二条消息。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from runtime.base_harness_v2 import BaseHarnessV2


class _ScriptedLLM:
    """第一轮出 tool_call，第二轮给答案。"""

    def __init__(self) -> None:
        self.calls: list[list[dict[str, Any]]] = []

    async def achat(
        self, messages: list[dict[str, Any]], tools: Any = None, **kwargs: Any
    ) -> dict[str, Any]:
        self.calls.append([dict(m) for m in messages])
        if len(self.calls) == 1:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "1",
                        "type": "function",
                        "function": {"name": "bash", "arguments": json.dumps({"cmd": "echo hi"})},
                    }
                ],
            }
        return {"role": "assistant", "content": "done"}


class _Tools:
    def names(self) -> list[str]:
        return ["bash"]

    def to_openai_schema(self) -> list[dict[str, Any]]:
        return []

    async def acall(self, name: str, **kwargs: Any) -> dict[str, Any]:
        return {"exit_code": 0, "stdout": "hi", "stderr": ""}


def test_tool_message_content_is_json_string() -> None:
    llm = _ScriptedLLM()
    h = BaseHarnessV2(
        {"system_prompt": "run bash"},
        {},
        {},
        {
            "constrain": {"require_human_approval": ["bash"], "forbidden_commands": ["rm -rf"]},
            "verify": {},
            "correct": {"max_retries": 1},
        },
        llm_client=llm,
        tool_registry=_Tools(),
        max_turns=3,
    )
    asyncio.run(h.run("run echo hi"))
    assert len(llm.calls) >= 2, "应至少两轮（工具调用 + 收尾）"
    tool_msgs = [m for m in llm.calls[1] if m.get("role") == "tool"]
    assert tool_msgs, f"第二轮必须带工具结果，实际={llm.calls[1]}"
    content = tool_msgs[0]["content"]
    assert isinstance(content, str), f"必须是字符串，实际 {type(content).__name__}"
    assert "hi" in content
