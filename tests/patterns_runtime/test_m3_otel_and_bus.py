"""优先级 3：OTel 事件接入；优先级 2 收尾：文件消息总线（a2a 真实适配器）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runtime.base_harness_v2 import BaseHarnessV2
from runtime.patterns.adapters import FileMessageBus


class _FakeTracer:
    def __init__(self) -> None:
        self.steps: list[tuple[Any, ...]] = []

    def on_step(self, run_id: Any, turn_index: int, event: str, detail: Any = None) -> None:
        self.steps.append((run_id, turn_index, event, detail))


def test_otel_tracer_receives_pattern_events() -> None:
    h = BaseHarnessV2({}, {}, {}, {})
    h.otel_tracer = _FakeTracer()
    h.PATTERNS = [{"pattern": "hitl", "approval-before": ["deploy"]}]
    from runtime.patterns import load

    load(h)
    h.constrain({"tool_name": "deploy", "args": {}})
    events = [s[2] for s in h.otel_tracer.steps]
    assert "pattern.hitl.on_tool_call" in events, f"tracer 应收到模式事件；实际 {events!r}"


def test_file_message_bus_persists_and_is_readable(tmp_path: Path) -> None:
    bus = FileMessageBus(tmp_path / "bus")
    h = BaseHarnessV2({}, {}, {}, {})
    h.PATTERNS = [{"pattern": "a2a", "protocol": "inmemory"}]
    from runtime.patterns import load

    load(h, adapters={"a2a": bus})
    res = h.patterns.api("a2a").send("worker-1", {"card": "c1", "id": "m1"})
    assert res["delivered"] is True
    inbox = (tmp_path / "bus" / "inbox.jsonl").read_text(encoding="utf-8")
    assert json.loads(inbox.strip())["to"] == "worker-1"
    assert bus.received("worker-1")[0]["payload"]["id"] == "m1"


def test_otel_absence_is_not_an_error() -> None:
    """反证：无 tracer 时一切照常（接入是可选的）。"""
    h = BaseHarnessV2({}, {}, {}, {})
    h.PATTERNS = [{"pattern": "hitl", "approval-before": ["deploy"]}]
    from runtime.patterns import load

    load(h)
    h.constrain({"tool_name": "deploy", "args": {}})
    assert h.patterns.events, "本地 events 仍应记录"
