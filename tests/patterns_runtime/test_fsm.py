"""契约 CT-FSM-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

import logging

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_fsm_behavior() -> None:
    h = _harness()
    h.PATTERNS = [
        {
            "pattern": "fsm",
            "initial-state": "idle",
            "states": ["idle->run:start", "run->done:finish"],
        }
    ]
    from runtime.patterns import load

    load(h)
    ff = h.patterns.api("fsm")
    assert ff.initial_state() == "idle"
    assert ff.transition("idle", "start") == "run"
    try:
        ff.transition("idle", "finish")
        raise AssertionError("非法迁移应报错")
    except ValueError:
        logging.getLogger(__name__).debug("swallowed exception", exc_info=True)
    assert "pattern:fsm" in str(h.build_context()), "CT-FSM-01：上下文应含指令"


def test_fsm_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:fsm" not in str(h.build_context())
