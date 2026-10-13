"""契约 CT-TOPIC_MODEL-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_topic_model_behavior() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "topic-model", "processor": "cluster-agent"}]
    from runtime.patterns import load

    load(h)
    tm = h.patterns.api("topic-model")
    assert tm.processor() == "cluster-agent"
    assert tm.retrieve("billing") == ["topic: billing"]
    assert set(tm.topics(["a", "b"])) == {"T0", "T1"}
    assert "pattern:topic-model" in str(h.build_context()), "CT-TOPIC_MODEL-01：上下文应含指令"


def test_topic_model_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:topic-model" not in str(h.build_context())
