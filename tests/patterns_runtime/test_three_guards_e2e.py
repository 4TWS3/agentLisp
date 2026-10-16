"""US-15 / US-17 / US-18：三段护栏与证据校验的端到端留痕。

US-15 constrain 段：危险命令被拦 + trace 留痕。
US-17 HITL：未获批的工具调用被拦 + patterns.events 留痕。
US-18 证据：回答无证据 id -> 拦 + patterns.events 留痕。
（US-16 verify 段由 runtime/tests/test_harness_v2.py::test_verify_failure_triggers_correct_then_circuit_breaker 覆盖。）
"""

from __future__ import annotations

import asyncio
from typing import Any

from runtime.base_harness_v2 import BaseHarnessV2
from runtime.patterns import load


class _BadLLM:
    async def achat(
        self, messages: list[dict[str, Any]], tools: Any = None, **kwargs: Any
    ) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "c1",
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
        raise AssertionError("危险命令不该被执行")


def test_constrain_blocks_forbidden_and_records() -> None:
    h = BaseHarnessV2(
        {},
        {},
        {},
        {"constrain": {"forbidden_commands": ["rm -rf"]}},
        llm_client=_BadLLM(),
        tool_registry=_Reg(),
    )
    trace = asyncio.run(h.run("trigger"))
    assert trace.status == "blocked", trace.status
    blocked = [m for m in h.trajectory if m.get("blocked")]
    assert blocked, "constrain 拦截没有留痕"


def _hitl_harness() -> BaseHarnessV2:
    h = BaseHarnessV2({}, {}, {}, {})
    h.PATTERNS = [{"pattern": "hitl", "approval-before": ["deploy"]}]
    load(h)
    return h


def test_hitl_blocks_unapproved_and_records_event() -> None:
    h = _hitl_harness()
    ok, why = h.patterns.on_tool_call({"tool_name": "deploy", "args": {}})
    assert ok is False, "未获批的执行必须被拦"
    assert "hitl" in why
    events = h.patterns.events_for("hitl")
    assert any(e["hook"] == "on_tool_call" for e in events), "HITL 拦截没有留痕"


def test_hitl_allows_approved() -> None:
    h = _hitl_harness()
    ok, why = h.patterns.on_tool_call({"tool_name": "deploy", "args": {"approved": True}})
    assert ok is True, why


def _rag_harness() -> BaseHarnessV2:
    h = BaseHarnessV2({}, {}, {}, {})
    h.PATTERNS = [{"pattern": "rag"}]
    load(h)
    return h


def test_rag_blocks_answer_without_evidence_and_records_event() -> None:
    h = _rag_harness()
    ok, why = h.patterns.verify_observation({"answer": "没有引用", "evidence_ids": ["doc-7"]})
    assert ok is False, "无证据引用必须被拦"
    assert why, "拦截必须给出原因"
    assert h.patterns.events_for("rag"), "证据拦截没有留痕"


def test_rag_passes_answer_with_evidence() -> None:
    h = _rag_harness()
    ok, why = h.patterns.verify_observation({"answer": "见 [doc-7]", "evidence_ids": ["doc-7"]})
    assert ok is True, why
