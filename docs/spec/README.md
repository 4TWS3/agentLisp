# docs/spec 索引（哪份是权威，哪份是什么）

> 2026-10-18 整理。**唯一权威的需求文档是 `agentlisp_srs.md`。**
> 其余文件是机器检查依赖、或被 SRS 引用的明细。

## 1. 权威文档

| 文件 | 地位 | 机器检查 |
|---|---|---|
| `agentlisp_srs.md` | **SRS（唯一权威）** | `scripts/check_roadmap_traceability.py` |

SRS §7 实况能力矩阵、§8 工作流与编排、§9 RSI 是**唯一**的能力口径。

## 2. 机器检查依赖（不可移）

| 文件 | 谁读它 |
|---|---|
| `c1_freeze_ratification.md` | `scripts/check_c1_freeze.py` |
| `agentlisp_pattern_landing.md` | `scripts/check_pattern_consistency.py`（口径短语） |
| `pattern_runtime_contracts/*.md` | `scripts/check_slot_model.py`、`scripts/check_contracts.py` |
| `agentlisp_observation_keys.md` | `scripts/check_observation_keys_doc.py` |

## 3. 明细参考（SRS 引用，不重复）

| 文件 | 内容 |
|---|---|
| `agentlisp-rsi-evolution-tech-spec.md` | RSI 设计草案 + as-built 横幅（SRS §9 是口径，这里是要点） |
| `agentlisp-pattern-macros-tech-spec.md` | 21 个模式宏的展开契约明细 |
| `cr42_pattern_language_level_design.md` | 模式落语言层的设计（`tests/test_cr42_pattern_language.py` 引用 §6） |
| `agentlisp-ams-decisions.md` / `agentlisp-ams-feature-spec.md` | AMS（LangGraph 适配器）侧文档，**不属于 agentLisp 核心** |
| `contracts-*.md` | 契约确认记录与草案 |
| `agentlisp_lessons_ledger.md` | 踩坑台账 |

## 4. 已归档

见 `docs/archive/spec/README.md`。
