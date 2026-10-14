"""M2 批 B 接线测试：reflect / guardrails-safety / reasoning / goal-setting 的观察门。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _h(*specs: dict) -> BaseHarnessV2:
    h = BaseHarnessV2({"system_prompt": "s"}, {}, {}, {})
    h.PATTERNS = list(specs)
    from runtime.patterns import load

    load(h)
    return h


def test_reflect_requires_reviewer_verdict() -> None:
    h = _h({"pattern": "reflect", "reviewer-agent": "critic"})
    ok, why = h.verify({"answer": "done"})
    assert not ok and "reflect" in why, f"缺 reviewer 应被拦；ok={ok}"
    ok2, _ = h.verify({"answer": "done", "reviewer": "critic: pass"})
    assert ok2, "有复核结论应放行"


def test_guardrails_requires_audit_record() -> None:
    h = _h({"pattern": "guardrails-safety", "hooks": ["pre", "post", "audit"]})
    ok, why = h.verify({"answer": "done"})
    assert not ok and "guardrails" in why, f"缺审计应被拦；ok={ok}"
    ok2, _ = h.verify({"answer": "done", "audit": "audit-1"})
    assert ok2, "有审计记录应放行"


def test_reasoning_requires_explicit_structure() -> None:
    h = _h({"pattern": "reasoning", "technique": "cot"})
    ok, why = h.verify({"answer": "42"})
    assert not ok and "reasoning" in why, f"缺推理结构应被拦；ok={ok}"
    ok2, _ = h.verify({"answer": "42", "reasoning": "step1; step2"})
    assert ok2, "有推理结构应放行"


def test_goal_setting_gates_progress() -> None:
    h = _h({"pattern": "goal-setting", "goal": "g"})
    ok, why = h.verify({"answer": "x", "progress": 0.5})
    assert not ok and "goal-setting" in why, f"进度未达目标应被拦；ok={ok}"
    ok2, _ = h.verify({"answer": "x", "progress": 1.0})
    assert ok2, "达成目标应放行"


def test_batch_b_counterproof_without_patterns() -> None:
    h = BaseHarnessV2({}, {}, {}, {})
    assert h.verify({"answer": "x"})[0], "反证：未声明批 B 模式不得拦"
