# US-06 交底：defmultiagent 内聚进 :workflow（D2）

> 判据：defmultiagent 与等价 :workflow 产物一致
> 结果：按 **B** 实现。结构同构（节点表相同、边集合相同）。

---

## 1. 结论

`:multiagent` 不再单独执行，降成 `:workflow` + `subagent` 节点。
`defmultiagent` 与等价显式 `:workflow` 的产物**结构同构**。

---

## 2. 改动

| 项 | 内容 |
|---|---|
| 节点类型 | 新增 `subagent` |
| 节点字段 | 新增 `:isolation`（`scoped`） |
| 内聚 | `parse-defagent` 把 `:multiagent` 降成 workflow（`multi->workflow`） |
| 移除 | `_multi_topology` / `_multi_workers`（此前是死字段，全仓无人读） |
| 产物 | `WORKFLOW.nodes[].isolation` |

---

## 3. 口径简化（必须说明）

多 agent 的 4 种拓扑全部**线性化为 DAG**：

| 拓扑 | 边 |
|---|---|
| orchestration | hub 扇出（w1→wi） |
| peer / decentralised / judge-driven | 链（wi→wi+1） |

理由：F-AMS-1 禁止未声明环，而 mesh/ring 天然有环。
若以后要表达环，用 `conditional-loop`。

---

## 4. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 等价 | pytest tests/test_cr43_multiagent_workflow.py | 2 passed |
| 4 拓扑 | 同上 | 每个都产出节点与边 |
| 宏回归 | pytest 宏/工作流/模式 | 见门禁 |

---

## 5. 未做

- 隔离语义只由 `:isolation scoped` 标注；运行期未按它调度（`scoped_worker` 仍手动调用）。
- mesh/ring 拓扑未表达（线性化）。
