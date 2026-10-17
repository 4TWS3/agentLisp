"""US-19 批 2：编排调度（router + parallel）。

判据：trace 含 worker 名 / 分支；未声明编排时走原循环。
"""

from __future__ import annotations

import asyncio
from typing import Any

from runtime.base_harness_v2 import BaseHarnessV2
from runtime.patterns import load


class _ToolLLM:
    async def achat(
        self, messages: list[dict[str, Any]], tools: Any = None, **kwargs: Any
    ) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "noop", "arguments": {}}}
            ],
        }


class _Reg:
    def names(self) -> list[str]:
        return ["noop"]

    def to_openai_schema(self) -> list[dict[str, Any]]:
        return []

    async def acall(self, name: str, **kwargs: Any) -> dict[str, Any]:
        return {"exit_code": 0, "stdout": "ok", "stderr": ""}


def _run(pattern: dict, user_input: str = "go") -> BaseHarnessV2:
    h = BaseHarnessV2({}, {}, {}, {}, llm_client=_ToolLLM(), tool_registry=_Reg())
    h.PATTERNS = [pattern]
    load(h)
    asyncio.run(h.run(user_input))
    return h


def test_router_spawns_the_mapped_worker() -> None:
    h = _run({"pattern": "router", "routes": ["deploy=>ops", "ask=>support"]}, "deploy")
    evs = h.patterns.events_for("orchestrator")
    spawns = [e["detail"] for e in evs if e["detail"]["action"] == "spawn"]
    assert spawns, evs
    assert spawns[0]["worker"] == "ops", "trace 里应有 worker 名"
    finishes = [e["detail"] for e in evs if e["detail"]["action"] == "finish"]
    assert finishes and finishes[-1]["report"]["worker"] == "ops"


def test_router_unknown_intent_is_a_clear_error() -> None:
    h = BaseHarnessV2({}, {}, {}, {}, llm_client=_ToolLLM(), tool_registry=_Reg())
    h.PATTERNS = [{"pattern": "router", "routes": ["deploy=>ops"]}]
    load(h)
    try:
        asyncio.run(h.run("nope"))
    except KeyError as exc:
        assert "未覆盖意图" in str(exc)
    else:
        raise AssertionError("未知意图应报错，不得静默")


def test_decomposition_recurses_to_max_depth() -> None:
    h = _run({"pattern": "decomposition", "max-depth": 2})
    evs = h.patterns.events_for("orchestrator")
    spawns = [e["detail"] for e in evs if e["detail"]["action"] == "spawn"]
    assert len(spawns) == 2, evs
    assert spawns[0]["worker"] == "subtask-0" and spawns[1]["worker"] == "subtask-1"
    finishes = [e["detail"] for e in evs if e["detail"]["action"] == "finish"]
    assert finishes and finishes[-1]["report"]["depth"] == 2
    assert len(finishes[-1]["report"]["tree"]) == 2, "层级应等于 max-depth"


def test_parallel_fans_out_branches_and_reports_fan_in() -> None:
    h = _run({"pattern": "parallel", "branches": ["a", "b"]})
    evs = h.patterns.events_for("orchestrator")
    fanouts = [e["detail"] for e in evs if e["detail"]["action"] == "fanout"]
    assert fanouts and fanouts[0]["branches"] == ["a", "b"]
    finishes = [e["detail"] for e in evs if e["detail"]["action"] == "finish"]
    assert finishes and finishes[-1]["report"]["fan_in"] == ["a", "b"]
