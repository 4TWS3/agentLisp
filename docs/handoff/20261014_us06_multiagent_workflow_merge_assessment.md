# US-06 交底：defmultiagent 与 :workflow 内聚评估（D2）

> 基线：19192c8 · 日期：2026-10-14
> 判据：defmultiagent 与等价 :workflow 产物一致
> 结果：**未达成**。按 D2 的翻转条件退回并列语法，原因已登记。

---

## 1. 结论

未达成。需要你确认走 D2 的翻转条件。

---

## 2. 为什么（实测判断）

D2 要求 `defmultiagent` 展开成 `:workflow` + 子 agent 节点。检查 `:workflow` 的表达力：

| 需要的 | `:workflow` 现状 |
|---|---|
| subagent 节点类型 | 只有 agent / computation / evaluator |
| scoped-worker 的上下文隔离 | 没有（靠 `_multi_workers` + `scoped_worker`） |
| worker 隔离测试 | 依赖 `:multiagent` 结构 |

**结论**：`:workflow` 覆盖不了多 agent 的隔离语义。

这正好命中 D2 自己写的翻转条件：
> 若 `:workflow` 的表达力无法覆盖 scoped-worker 的隔离语义，则退回并列语法并登记原因。

---

## 3. 现状

- `:multiagent` 与 `:workflow` 并列存在。
- 二者**同一文件内互斥**（F-AMS-1 草案：编译期拦）。这是安全规则，不是 D2 的「同一模型两种入口」。

---

## 4. 需要你决定（三选一）

| 选项 | 影响 | 建议 |
|---|---|---|
| A. 按翻转条件：保留并列 + 互斥，写清原因 | 不动隔离语义；US-06 判据不达成 | **建议** |
| B. 实现 `:workflow` 的 subagent 节点 + 隔离语义 | 大改：节点类型、隔离、测试迁移 | 不建议现在做 |
| C. 只做结构同构，放弃隔离 | 破坏跨 worker 隔离测试 | 不作 |

---

## 5. 验证

- `:workflow` / `:multiagent` 既有测试全绿。
- 互斥规则：tests/test_cr43_workflow.py::test_workflow_and_multiagent_are_mutually_exclusive
