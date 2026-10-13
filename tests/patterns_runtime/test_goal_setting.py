"""契约 CT-GOAL_SETTING-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_goal_setting_behavior() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "goal-setting", "goal": "提高核销率"}]
    from runtime.patterns import load

    load(h)
    gg = h.patterns.api("goal-setting")
    assert gg.goal() == "提高核销率"
    assert gg.deviation(0.5) is True and gg.deviation(1.0) is False
    assert "pattern:goal-setting" in str(h.build_context()), "CT-GOAL_SETTING-01：上下文应含指令"


def test_goal_setting_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:goal-setting" not in str(h.build_context())
