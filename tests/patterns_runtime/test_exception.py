"""契约 CT-EXCEPTION-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from typing import Any

from runtime.base_harness_v2 import BaseHarnessV2


def _harness(**kwargs: Any) -> BaseHarnessV2:
    return BaseHarnessV2(
        {}, {}, {}, {"correct": {"max_retries": 5, "on_failure": "abort"}}, **kwargs
    )


def test_ct_exception_01_behavior_policy_and_directive() -> None:
    """行为：带 :pattern exception → 策略生效（不放宽既有保护）+ 上下文指令。"""
    h = _harness()
    h.PATTERNS = [{"pattern": "exception", "retries": 3, "backoff": "exponential"}]
    from runtime.patterns import load

    load(h)
    assert h.patterns.retry_policy() == {"retries": 3, "backoff": "exponential"}, (
        "CT-EXCEPTION-01：应返回 min(3, max_retries=5) = 3"
    )
    assert "pattern:exception" in str(h.build_context()), "CT-EXCEPTION-01：上下文应含指令"
    assert h.patterns.landed() == ["exception"]


def test_ct_exception_01_counterproof_without_pattern_is_baseline() -> None:
    """反证：不带 :pattern → 无策略、无指令。"""
    h = _harness()
    assert h.patterns.retry_policy() == {}, "反证：未声明时策略必须为空"
    assert h.patterns.handlers == [], "未声明模式不得载入 handler"
    assert "pattern:exception" not in str(h.build_context())
