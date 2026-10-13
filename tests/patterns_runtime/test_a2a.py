"""契约 CT-A2A-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_a2a_behavior() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "a2a", "protocol": "inmemory"}]
    from runtime.patterns import load

    load(h)
    aa = h.patterns.api("a2a")
    assert aa.protocol() == "inmemory"
    res = aa.send("worker-1", {"card": "card-7", "id": "m1"})
    assert res["delivered"] is True and aa.bus.sent[0]["to"] == "worker-1"
    assert "pattern:a2a" in str(h.build_context()), "CT-A2A-01：上下文应含指令"


def test_a2a_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:a2a" not in str(h.build_context())
