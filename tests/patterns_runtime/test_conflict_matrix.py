"""设计 v2 §6 的冲突矩阵测试：枚举 21×21 对。

规则（§6）：
  * 同组两成员 → 启动失败，错误信息**点名双方 kind** 与组名
  * 跨组两成员 → 启动成功；钩子调用顺序 == 声明顺序
  * 同一 kind ×2 → 幂等（只载入一个 handler）
"""

from __future__ import annotations

import itertools

import pytest

from runtime.base_harness_v2 import BaseHarnessV2
from runtime.patterns import GROUPS, load

# 21 个 kind 的合法 spec（键取自编译期注册表）
VALID: dict[str, dict] = {
    "priority": {"pattern": "priority", "criteria": "urgency", "levels": 3},
    "exception": {"pattern": "exception", "retries": 2, "backoff": "linear"},
    "reflect": {"pattern": "reflect", "reviewer-agent": "critic"},
    "evaluator": {"pattern": "evaluator", "thresholds": [0.4, 0.8]},
    "guardrails-safety": {"pattern": "guardrails-safety", "hooks": ["pre", "post", "audit"]},
    "hitl": {"pattern": "hitl", "approval-before": ["deploy"]},
    "rag": {"pattern": "rag"},
    "reasoning": {"pattern": "reasoning", "technique": "cot"},
    "router": {"pattern": "router", "routes": ["a=>w1"]},
    "chain": {"pattern": "chain", "steps": ["s1", "s2"]},
    "parallel": {"pattern": "parallel", "branches": ["b1"]},
    "planner": {"pattern": "planner", "plan-size": 3},
    "decomposition": {"pattern": "decomposition", "max-depth": 2},
    "fsm": {"pattern": "fsm", "initial-state": "idle", "states": ["idle->run:start"]},
    "decomposer": {"pattern": "decomposer", "schema-fields": ["name"]},
    "exploration": {"pattern": "exploration", "budget": 3, "convergence": 0.01},
    "resource-aware": {"pattern": "resource-aware", "budget": "low"},
    "goal-setting": {"pattern": "goal-setting", "goal": "g"},
    "topic-model": {"pattern": "topic-model", "processor": "p"},
    "a2a": {"pattern": "a2a", "protocol": "inmemory"},
    "learning": {"pattern": "learning", "skill-dir": "skills"},
}

KINDS = sorted(VALID)
# 设计 §6 的 8 个互斥组覆盖 19 个 kind；priority 与 reasoning 不参与互斥（独立），
# 故各自给一个唯一组名，避免被误判成同组。
GROUP_OF = {k: g for g, members in GROUPS.items() for k in members}
for _k in KINDS:
    GROUP_OF.setdefault(_k, f"独立:{_k}")
_CROSS = [(a, b) for a, b in itertools.combinations(KINDS, 2) if GROUP_OF[a] != GROUP_OF[b]]
_SAME = [(a, b) for a, b in itertools.combinations(KINDS, 2) if GROUP_OF[a] == GROUP_OF[b]]


def _load(*kinds: str):
    h = BaseHarnessV2({}, {}, {}, {})
    h.PATTERNS = [dict(VALID[k]) for k in kinds]
    load(h)
    return h


def test_matrix_is_complete() -> None:
    """矩阵必须覆盖全部 21 个 kind 与全部 210 个两两组合。"""
    assert len(KINDS) == 21, f"kind 数应为 21，实际 {len(KINDS)}"
    assert len(_CROSS) + len(_SAME) == 210, "两两组合数应为 C(21,2)=210"
    assert len(_SAME) >= 1 and len(_CROSS) >= 1, "同组与跨组都应有样本"


@pytest.mark.parametrize(("a", "b"), _SAME)
def test_same_group_pair_fails_and_names_both(a: str, b: str) -> None:
    """同组两成员：启动失败，且错误信息点名双方 kind 与组名。"""
    h = BaseHarnessV2({}, {}, {}, {})
    h.PATTERNS = [dict(VALID[a]), dict(VALID[b])]
    with pytest.raises(ValueError) as ei:
        load(h)
    msg = str(ei.value)
    assert a in msg and b in msg, f"错误应点名双方；实际 {msg!r}"
    assert GROUP_OF[a] in msg, f"错误应含组名 {GROUP_OF[a]!r}；实际 {msg!r}"


@pytest.mark.parametrize(("a", "b"), _CROSS)
def test_cross_group_pair_loads_in_declaration_order(a: str, b: str) -> None:
    """跨组两成员：启动成功，且 handler 顺序 == 声明顺序（含反向）。"""
    assert [h.kind for h in _load(a, b).patterns.handlers] == [a, b]
    assert [h.kind for h in _load(b, a).patterns.handlers] == [b, a]


def test_same_kind_twice_is_idempotent() -> None:
    """同一 kind ×2：幂等，只载入一个 handler。"""
    h = _load("priority", "priority")
    assert [x.kind for x in h.patterns.handlers] == ["priority"]


def test_all_kinds_load_alone() -> None:
    """21 个 kind 各自单独声明都能载入（矩阵的前提）。"""
    for k in KINDS:
        assert [x.kind for x in _load(k).patterns.handlers] == [k], f"{k} 单独声明应可载入"
