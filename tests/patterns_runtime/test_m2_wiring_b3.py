"""M2 第三批接线测试：fsm 状态校验 / decomposer 字段门 / evaluator 阈值门 / resource-aware 档位。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness(**kw: object) -> BaseHarnessV2:
    return BaseHarnessV2({"system_prompt": "s"}, {}, {}, {}, **kw)


def _load(h: BaseHarnessV2) -> None:
    from runtime.patterns import load

    load(h)


def test_fsm_blocks_illegal_transition() -> None:
    h = _harness()
    h.PATTERNS = [
        {"pattern": "fsm", "initial-state": "idle", "states": ["idle->run:start", "run->done:stop"]}
    ]
    _load(h)
    ok, _ = h.constrain({"tool_name": "start", "args": {}})
    assert ok, "合法迁移应放行"
    bad, why = h.constrain({"tool_name": "start", "args": {}})
    assert not bad and "fsm" in why, f"非法迁移应被拦；ok={bad} why={why!r}"


def test_decomposer_gates_missing_fields() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "decomposer", "schema-fields": ["name", "kind"]}]
    _load(h)
    ok, why = h.verify({"fields": {"name": "a"}})
    assert not ok and "decomposer" in why, f"字段缺失应被拦；ok={ok}"
    ok2, _ = h.verify({"fields": {"name": "a", "kind": "b"}})
    assert ok2, "字段齐全应放行"


def test_evaluator_gates_low_score() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "evaluator", "thresholds": [0.4, 0.8]}]
    _load(h)
    ok, why = h.verify({"score": 0.2})
    assert not ok and "evaluator" in why, f"低分应被拦；ok={ok}"
    ok2, _ = h.verify({"score": 0.9})
    assert ok2, "高分应放行"


def test_resource_aware_writes_tier() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "resource-aware", "budget": "low"}]
    _load(h)
    assert h.model_config.get("tier") == "small", "档位应写入 model_config"


def test_m2c_counterproof_without_patterns_is_baseline() -> None:
    h = _harness()
    assert h.constrain({"tool_name": "start", "args": {}})[0], "反证：未声明 fsm 不得拦"
    assert h.verify({"fields": {"name": "a"}})[0], "反证：未声明 decomposer 不得拦"
    assert h.verify({"score": 0.1})[0], "反证：未声明 evaluator 不得拦"
    assert "tier" not in h.model_config, "反证：未声明 resource-aware 不得写档位"
