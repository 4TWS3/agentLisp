# US-19 交底：编排调度（批 1 chain + planner）

> 基线：a5e6943 · 日期：2026-10-14
> 判据：5 个编排 kind 的 trace 含步骤与 worker 名
> 结果：**部分**。批 1 完成；批 2/3 待做。

---

## 1. 结论

批 1 完成：新增 `runtime/orchestrator.py` 的唯一决策点 `select_next`，
harness 每轮先问编排器，`finish` 即结束，全程留痕。
批 2（router + parallel）/ 批 3（decomposition）未做。

---

## 2. 设计依据

`docs/spec/agentlisp_orchestrator_design.md` §8 里程碑：
批 1 = 1–2 工程日；批 2 = 2–3；批 3 = 2–4。**这是多日工作**，一轮不能全做完。

---

## 3. 批 1 交付

| 文件 | 内容 |
|---|---|
| runtime/orchestrator.py | `Action`（step/spawn/fanout/finish）+ `Orchestrator.select_next` |
| runtime/base_harness_v2.py | 每轮先问编排器；`finish` 即结束；事件留痕 |
| runtime/patterns/__init__.py | `load()` 后重建编排器 |
| tests/test_orchestrator_batch1.py | 4 条（chain / planner / 确定性 / 反证） |

---

## 4. 判据覆盖（诚实分档）

| kind | trace 含步骤 | trace 含 worker 名 |
|---|---|---|
| chain | **是**（steps 序列） | 否（顺序类无 worker） |
| planner | **是**（plan + 完成度） | 否 |
| router | 未做 | 未做 |
| parallel | 未做 | 未做 |
| decomposition | 未做 | 未做 |

---

## 5. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 编排批 1 | pytest tests/test_orchestrator_batch1.py | 4 passed |
| harness 回归 | pytest runtime/tests/test_harness_v2.py | 38 passed |

---

## 6. 未做

- 批 2：router（spawn）/ parallel（fanout + fan_in + 假时钟）。
- 批 3：decomposition（递归 + max-depth）。
- 「前一步输出注入下一步上下文」未做（当前只记录步骤名，不改提示）。
- `orchestrate` 槽位仍 pending（编排器在 harness 层，不是 pattern 槽位）。
