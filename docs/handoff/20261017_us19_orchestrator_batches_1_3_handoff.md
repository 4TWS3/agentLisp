# US-19 交底：编排调度批 1-3（5 个编排 kind）

> 判据：5 个编排 kind 的 trace 含步骤与 worker 名

---

## 1. 结论

5 个编排 kind 全部进编排器。trace 含步骤名、worker 名、分支、子任务层级。

---

## 2. 各 kind 在 trace 里的样子

| kind | Action | trace 含 |
|---|---|---|
| chain | step（每步一条） | 步骤名序列 |
| planner | step（plan + 各步） | plan 与完成度 |
| router | spawn(worker) | worker 名（如 ops） |
| parallel | fanout(branches) | 分支名 |
| decomposition | spawn(subtask-N) | 层级与子任务树 |

---

## 3. 实现

- `runtime/orchestrator.py`：`select_next` 覆盖 5 kind；决策只看 state（步数/意图），不读时间/随机。
- `BaseHarnessV2`：每轮先问编排器；`finish` 即结束；事件写进 `patterns.events`。

---

## 4. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 批 1（chain/planner） | pytest tests/test_orchestrator_batch1.py | 4 passed |
| 批 2/3（router/parallel/decomposition） | pytest tests/test_orchestrator_batch2.py | 4 passed |

---

## 5. 未做（诚实登记）

- **没有真的子 agent 执行**：spawn / fanout 只记录决策，子任务仍走同一个 ReAct 循环。
- **没有真并发**：只有分支记录，没有并行跑。
- `orchestrate` 槽位仍 pending（编排器在 harness 层，不是 pattern 槽位）。
