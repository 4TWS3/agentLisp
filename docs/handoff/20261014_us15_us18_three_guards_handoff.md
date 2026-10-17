# US-15 / US-16 / US-17 / US-18 交底：三段护栏 + 证据校验

> 基线：1a1c34a · 日期：2026-10-14
> 判据：constrain / verify / HITL / 证据，四段生效 + 留痕

---

## 1. 结论

四段都生效。本轮补上一个**留痕缺口**：证据门控此前拦了但不记录。

---

## 2. 判据映射

| 故事 | 判据 | 证据 |
|---|---|---|
| US-15 | 危险命令被拦 + 留痕 | tests/patterns_runtime/test_three_guards_e2e.py::test_constrain_blocks_forbidden_and_records |
| US-16 | verify 段生效 | runtime/tests/test_harness_v2.py::test_verify_failure_triggers_correct_then_circuit_breaker |
| US-17 | 未获批不得执行 + 留痕 | test_three_guards_e2e.py::test_hitl_blocks_unapproved_and_records_event |
| US-18 | 无证据 id -> 拦 + 留痕 | test_three_guards_e2e.py::test_rag_blocks_answer_without_evidence_and_records_event |

---

## 3. 修的缺口

`PatternRuntime._verify_observation_impl` 的三个门（rag 证据 / decomposer 字段 / evaluator 阈值）
此前**只返回结果，不记录**。已补：每个门记 `{ok, why}` 事件。

---

## 4. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 三护栏 | pytest tests/patterns_runtime/test_three_guards_e2e.py | 5 passed |
| 模式全集 | pytest tests/patterns_runtime/ | 311 passed |
| 判据 | python3 tools/standards_check.py | 19 通过 / 0 失败 |

---

## 5. 未做

无（本故事判据范围内的项已全部交付）。
