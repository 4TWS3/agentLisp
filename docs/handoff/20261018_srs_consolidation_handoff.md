# SRS 回溯与文档收口（2026-10-18）

> 判据：一份完整 SRS + 分散的 spec 有明确归属

---

## 1. 结论

- **`docs/spec/agentlisp_srs.md` 是唯一权威需求文档**，新增 §7/§8/§9。
- 4 份设计 spec 归档到 `docs/archive/spec/`（**没有删除**）。
- 新增两份索引：`docs/spec/README.md`、`docs/archive/spec/README.md`。

---

## 2. SRS 新增的三章

| 章 | 内容 |
|---|---|
| §7 实况能力矩阵 | 19 项能力的 as-built 状态 + 三条机器不变式 + 已知未做 |
| §8 工作流与编排 | `:workflow` 语法、LangGraph 分工、`:reducer` 语义 |
| §9 RSI | 定位（agent 自己的制品，不是编译器）、双循环、5 条 FR-EVO、实测边界 |

判据只认机器可复现证据（测试文件 / 编译产物 / 实测命令）。

---

## 3. 归档清单

| 原文件 | 被谁取代 |
|---|---|
| `agentlisp_specification.md` | SRS 全文 |
| `agentlisp_orchestrator_design.md` | SRS §8 |
| `agentlisp_pattern_runtime_design.md` | SRS §7 |
| `agentlisp_pattern_review_package.md` | SRS §7 |

引用它们的旧文档已同步改路径（AMS feature spec、master plan、machine-verification-report）。
`docs/handoff/` 里的历史交底不更新（属快照）。

---

## 4. 保留在 docs/spec 的文件及理由

| 文件 | 为什么留 |
|---|---|
| `c1_freeze_ratification.md` | `check_c1_freeze.py` 读它 |
| `agentlisp_pattern_landing.md` | `check_pattern_consistency.py` 读口径短语 |
| `pattern_runtime_contracts/` | `check_slot_model.py` / `check_contracts.py` 读它 |
| `agentlisp_observation_keys.md` | `check_observation_keys_doc.py` 读它 |
| `agentlisp-rsi-evolution-tech-spec.md` | RSI 设计与 as-built 明细（SRS §9 是口径） |
| `agentlisp-pattern-macros-tech-spec.md` | 21 个模式宏的展开契约明细 |
| `cr42_pattern_language_level_design.md` | `tests/test_cr42_pattern_language.py` 引用 §6 |
| `agentlisp-ams-*.md` | AMS 侧文档，不属于 agentLisp 核心 |
| `contracts-*.md` / `lessons_ledger` | 契约记录 / 踩坑台账 |

---

## 5. 验证

| 项 | 结果 |
|---|---|
| `check_roadmap_traceability.py --srs ...` | exit=0（`rows=47` 是既有告警，非本次引入） |
| `tools/standards_check.py` | 19/0 |
| `ruff check` | 全过 |
| git | 4 个 rename + 2 个索引 + 3 处引用修正 |
