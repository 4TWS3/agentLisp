"""US-14：模式 handler 抛错不得拖垮 Agent（P1-3a）。

判据：handler 抛错被捕获 + 留痕 + 有测试。
增强钩子（before_turn / after_turn / order）失败 -> 跳过（原值）。
安全钩子（on_tool_call / verify_observation）失败 -> 按拒绝（fail-closed），不静默放行。
"""

from __future__ import annotations

from typing import Any

import pytest

import runtime.patterns as patterns_mod
from runtime.base_harness_v2 import BaseHarnessV2
from runtime.patterns import load


def _harness(kind: str, spec: dict | None = None) -> BaseHarnessV2:
    h = BaseHarnessV2({}, {}, {}, {})
    h.PATTERNS = [{"pattern": kind} if spec is None else spec]
    load(h)
    return h


class _Boom:
    kind = "priority"

    def __init__(self, spec: dict) -> None:
        self.spec = spec

    def on_init(self, harness: Any, others: list[str]) -> None:
        return None

    def before_turn(self, harness: Any, ctx: dict) -> dict:
        raise RuntimeError("boom before_turn")

    def on_tool_call(self, harness: Any, call: dict) -> tuple[bool, str]:
        raise RuntimeError("boom on_tool_call")

    def after_turn(self, harness: Any, ctx: dict) -> dict:
        raise RuntimeError("boom after_turn")

    def order(self, candidates: list[dict]) -> list[dict]:
        raise RuntimeError("boom order")


@pytest.fixture
def boom(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(patterns_mod.HANDLERS, "priority", _Boom)


def test_before_turn_error_is_caught_and_recorded(boom: None) -> None:
    h = _harness("priority", {"pattern": "priority", "criteria": "u"})
    ctx = h.patterns.before_turn({"messages": []})
    assert ctx == {"messages": []}, "抛错后上下文应原样返回，不崩"
    assert h.patterns.events_for("priority"), "必须留痕"


def test_on_tool_call_error_fails_closed(boom: None) -> None:
    h = _harness("priority", {"pattern": "priority", "criteria": "u"})
    ok, why = h.patterns.on_tool_call({"tool_name": "bash", "args": {}})
    assert ok is False, "安全钩子抛错应拒绝，不静默放行"
    assert "抛错" in why
    assert h.patterns.events_for("priority")


def test_after_turn_error_is_caught(boom: None) -> None:
    h = _harness("priority", {"pattern": "priority", "criteria": "u"})
    assert h.patterns.after_turn({"messages": []}) == {"messages": []}


def test_order_error_returns_original(boom: None) -> None:
    h = _harness("priority", {"pattern": "priority", "criteria": "u"})
    cands = [{"id": "a"}, {"id": "b"}]
    assert h.patterns.order(cands) == cands


class _BoomRag:
    kind = "rag"

    def __init__(self, spec: dict) -> None:
        self.spec = spec

    def on_init(self, harness: Any, others: list[str]) -> None:
        return None

    def before_turn(self, harness: Any, ctx: dict) -> dict:
        return ctx

    def on_tool_call(self, harness: Any, call: dict) -> tuple[bool, str]:
        return True, ""

    def after_turn(self, harness: Any, ctx: dict) -> dict:
        return ctx

    def verify_evidence(self, answer: str, ids: list[str]) -> tuple[bool, str]:
        raise RuntimeError("boom verify")


def test_verify_observation_error_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(patterns_mod.HANDLERS, "rag", _BoomRag)
    h = _harness("rag", {"pattern": "rag"})
    ok, why = h.patterns.verify_observation({"answer": "a", "evidence_ids": ["e1"]})
    assert ok is False, "门控抛错应拒绝，不静默放行"
    assert "抛错" in why
