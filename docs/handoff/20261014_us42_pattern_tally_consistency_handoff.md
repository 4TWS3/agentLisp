# US-42 交底：口径三处一致（含机器核对脚本）

> 基线：`03e3596` · 日期：2026-10-14
> 故事：US-42（作为 A，我要口径三处一致，以便文档可信）
> 判据：README / LANDED 注释 / patterns README 数字一致，脚本可核对

---

## 1. 三处指哪里

| 处 | 文件 |
|---|---|
| README | `README.md` 头部「引擎消费口径」 |
| LANDED 注释 | `runtime/patterns/__init__.py` 的 LANDED 注释 |
| 落地清单 | `docs/spec/agentlisp_pattern_landing.md`（脚本生成） |

---

## 2. 之前为什么不一致

同一件事有三个数与三个词。

| 处 | 旧写法 | 问题 |
|---|---|---|
| README | 「21/21 运行时落地」+「13/21 真消费」 | 两个「落地」含义不同 |
| LANDED 注释 | 「已落地的 kind」21 个 | 只给 21，不提 8 个仅声明 |
| 落地清单 | 「21 = V1 5 + V2 16」 | 只统计宏，不提消费 |

---

## 3. 修法：唯一真源 + 核对脚本

- **唯一真源**：`runtime/patterns/__init__.py` 新增 `DECLARED_ONLY`（8）
  与 `ENGINE_CONSUMED = LANDED - DECLARED_ONLY`（13）。
- **三处逐字**含同一短语：`落地 21 / 引擎消费 13 / 仅声明 8`。
- 生成器 `scripts/pattern_landing_report.py` 从真源取数，清单不再手写。
- 核对脚本 `scripts/check_pattern_consistency.py`：任一出处缺短语即 rc=1。
- 测试 `tests/test_pattern_consistency.py` 把脚本接进门禁。

---

## 4. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 一致 | `python3 scripts/check_pattern_consistency.py` | `OK 三处口径一致：落地 21 / 引擎消费 13 / 仅声明 8`，rc=0 |
| 注入漂移 | 把 README 的 21 改成 99 再跑 | `FAIL README.md`，rc=1 |
| 守卫 | `pytest tests/test_pattern_consistency.py -q --no-cov` | 1 passed |
| 清单 | `python3 scripts/pattern_landing_report.py` | 21/21 齐全 |
| 判据 | `python3 tools/standards_check.py` | 17 通过 / 0 失败 |

---

## 5. 代价与未做

- `DECLARED_ONLY` 是**声明式台账**，来自机器验证报告 §4.2 的实测，不是从调用点反推。
  槽位模型（US-30 / P1-1）会把它变成结构化事实。已写进代码注释。
- 本故事**不修**「8 个仅声明」本身。那是 US-26。本故事只保证口径诚实。
