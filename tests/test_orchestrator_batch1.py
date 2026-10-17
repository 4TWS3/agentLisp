"""US-19 批 1：编排调度（chain + planner）。

判据（设计 §1）：行为可观测 / 声明驱动 / 确定性 / 未声明编排时走原循环。
批 2/3（router / parallel / decomposition）待做。
"""

from __future__ import annotations

import asyncio
from typing import Any

from runtime.base_harness_v2 import BaseHarnessV2
from runtime.orchestrator import Action, Orchestrator, build_orchestrator
from runtime.patterns import load


class _ToolLLM:
    """每轮都出 tool_call，让循环继续，直到编排器 finish。"""

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


def _run(pattern: dict) -> BaseHarnessV2:
    h = BaseHarnessV2({}, {}, {}, {}, llm_client=_ToolLLM(), tool_registry=_Reg())
    h.PATTERNS = [pattern]
    load(h)
    asyncio.run(h.run("go"))
    return h


def test_chain_records_steps_then_finishes() -> None:
    h = _run({"pattern": "chain", "steps": ["a", "b"]})
    acts = [e["detail"]["action"] for e in h.patterns.events_for("orchestrator")]
    assert "step" in acts and "finish" in acts, acts
    tasks = [e["detail"]["task"] for e in h.patterns.events_for("orchestrator")]
    assert tasks[:2] == ["a", "b"], tasks


def test_planner_records_plan_then_completion() -> None:
    h = _run({"pattern": "planner", "plan-size": 2})
    evs = h.patterns.events_for("orchestrator")
    tasks = [e["detail"]["task"] for e in evs]
    assert tasks[0] == "plan"
    finishes = [e["detail"] for e in evs if e["detail"]["action"] == "finish"]
    assert finishes and finishes[-1]["report"]["completion"] == 1.0


def test_select_next_is_deterministic() -> None:
    h = BaseHarnessV2({}, {}, {}, {})
    h.PATTERNS = [{"pattern": "chain", "steps": ["x", "y"]}]
    load(h)
    o = h.orchestrator
    assert isinstance(o, Orchestrator)
    assert (
        o.select_next({"step_index": 0})
        == o.select_next({"step_index": 0})
        == Action("step", task="x")
    )
    assert o.select_next({"step_index": 9}).kind == "finish"


def test_no_orchestration_keeps_baseline() -> None:
    """反证：不声明编排模式 -> 无编排器、无编排事件。"""
    h = BaseHarnessV2({}, {}, {}, {}, llm_client=_ToolLLM())
    load(h)
    assert build_orchestrator(h.patterns) is None
    asyncio.run(h.run("go"))
    assert h.patterns.events_for("orchestrator") == []
