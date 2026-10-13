"""M2 第二批接线测试：exception 收紧重试 / exploration 收紧轮次 / rag 观察门。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {"correct": {"max_retries": 5, "on_failure": "abort"}})


def test_exception_tightens_retries_but_never_loosens() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "exception", "retries": 2, "backoff": "linear"}]
    from runtime.patterns import load

    load(h)
    assert h.patterns.retries_cap(5) == 2, "模式只能收紧（min(5,2)=2）"
    assert h.patterns.retries_cap(1) == 1, "已有限制更严时保持 1（不放宽）"


def test_exploration_tightens_turn_budget() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "exploration", "budget": 3, "convergence": 0.01}]
    from runtime.patterns import load

    load(h)
    assert h.patterns.turn_budget(30) == 3, "轮次上限应被收紧到 3"


def test_rag_gates_observation_without_evidence() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "rag"}]
    from runtime.patterns import load

    load(h)
    ok, why = h.verify({"answer": "结论：可以发布", "evidence_ids": ["doc-7"]})
    assert not ok and "rag" in why, f"无引用应被拦；ok={ok} why={why!r}"
    ok2, _ = h.verify({"answer": "结论：可以发布，见 doc-7", "evidence_ids": ["doc-7"]})
    assert ok2, "引用了证据应放行"


def test_m2b_counterproof_without_patterns_is_baseline() -> None:
    h = _harness()
    assert h.patterns.retries_cap(5) == 5, "反证：未声明 exception 不得改重试"
    assert h.patterns.turn_budget(30) == 30, "反证：未声明 exploration 不得改轮次"
    ok, _ = h.verify({"answer": "无引用", "evidence_ids": ["doc-7"]})
    assert ok, "反证：未声明 rag 不得拦观察值"
