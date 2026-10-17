"""US-43：证据链能定位首错（ExecutionTraceV2.first_error + 结构化错误）。"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from runtime.base_harness_v2 import BaseHarnessV2, ExecutionTraceV2


class _BadLLM:
    async def achat(
        self, messages: list[dict[str, Any]], tools: Any = None, **kwargs: Any
    ) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "1",
                    "type": "function",
                    "function": {"name": "bash", "arguments": {"command": "rm -rf /"}},
                }
            ],
        }


class _Reg:
    def names(self) -> list[str]:
        return ["bash"]

    def to_openai_schema(self) -> list[dict[str, Any]]:
        return []

    async def acall(self, name: str, **kwargs: Any) -> Any:
        raise AssertionError("不该执行")


def test_blocked_run_records_first_error() -> None:
    h = BaseHarnessV2(
        {},
        {},
        {},
        {"constrain": {"forbidden_commands": ["rm -rf"]}},
        llm_client=_BadLLM(),
        tool_registry=_Reg(),
    )
    trace = asyncio.run(h.run("go"))
    assert trace.status == "blocked"
    fe = trace.first_error
    assert fe is not None
    assert fe.code == "BLOCKED"
    assert fe.stage == "constrain"
    dumped = trace.to_dict()
    assert dumped["first_error"]["code"] == "BLOCKED"
    assert dumped["first_error"]["message"]


def test_first_error_keeps_the_first() -> None:
    h = BaseHarnessV2({}, {}, {}, {})
    h._trace = ExecutionTraceV2(run_id="r", agent_name=None, started_at=datetime.now(UTC))
    h._set_error("A", "first", "loop")
    h._set_error("B", "second", "exception")
    assert h._trace.error == "second"
    assert h._trace.first_error is not None
    assert h._trace.first_error.code == "A"
