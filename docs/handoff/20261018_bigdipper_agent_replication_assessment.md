# bigdipper 全 agent 复刻评估（2026-10-18）

> 问题：用 agentLisp 能不能把这些 agent **复刻**出来

---

## 1. 结论

**5 个图型 agent 里 4 个可直接复刻；2 个非图架构要重新设计；1 个不是 agent。**

---

## 2. 逐个体检（机器提取）

| Agent | py 文件 | 行数 | 节点 | 条件边 | interrupt | 图形态 |
|---|---:|---:|---:|---:|---:|---|
| `agents/triz-agent` | 8 | 858 | 5 | 0 | 0 | 线性 |
| `beidou/tianji` | 106 | 33,640 | 6 | 0 | 0 | 线性 + 1 个 dict reducer |
| `beidou/tianxuan` | 37 | 5,742 | 11 | **6** | **6** | 分支 + 入口路由 + 回指 END |
| `agents/spec-writer` | 34 | 2,939 | 15 | **5** | **10** | 分支 + 澄清环 |
| `beidou/yaoguang` | 29 | 4,365 | 0 | 0 | 0 | **无图**：自定义循环 + switch_phase 工具 |
| `beidou/xuanji` | 14 | 2,076 | 0 | 0 | 0 | **无图**：orchestrator（decompose/route/dispatch/integrate） |
| `shared/knowledge` | 57 | 15,102 | 0 | 0 | 0 | 不是 agent（13 处 subprocess，知识库工具） |

---

## 3. 复刻判定

| Agent | 判定 | 说明 |
|---|---|---|
| triz-agent | ✅ **可直接复刻** | 5 节点线性图，无 state 累积、无条件分支 |
| tianji | ✅ **可直接复刻** | 线性 6 节点 + `chapters` dict 累积 = `:reducer merge` |
| tianxuan | ✅ **可复刻** | 11 节点 + 6 条件边；本轮补了「条件边指向 END」与「入口条件是路由」 |
| spec-writer | ✅ **可复刻** | 15 节点 + 5 条件边 + 澄清环；子进程走 handler |
| yaoguang | ⚠️ **要重新设计** | 它不是图：是一个循环 + `switch_phase` 工具 + `prompt_assembler`。用「单 Agent + 工具」能复刻行为，但阶段机要重写 |
| xuanji | ⚠️ **部分** | dispatch 可用 `subagent` 路由；decompose/route/integrate 是自定义 handler；并行由 handler 自己 `asyncio.gather` |
| shared/knowledge | ❌ **不是 agent** | 没有节点、没有 LLM 调用，应作为 **tool** 接进来 |

---

## 4. 本轮补的两个能力（tianxuan 需要）

| 能力 | 之前 | 现在 |
|---|---|---|
| 条件边指向 END | 映射成字符串 `"END"`（会当成节点名） | 映射成真正的 `END` 哨兵 |
| 入口条件路由 | 只支持固定 `:entry` | `build_graph(..., entry_router=fn)` |

---

## 5. 仍然不覆盖的（诚实登记）

| 项 | 影响 |
|---|---|
| `interrupt()` 不在 DSL 里声明 | 节点内可直接调 LangGraph 的 `interrupt`，能用，但**不可静态校验**；恢复时会重跑整个节点 |
| 并行 fan-out | 桥不管，handler 自己 `asyncio.gather`（xuanji 的做法） |
| 领域逻辑 | OLAP 立方体 / PDF / 知识库检索必须 Python 实现 |

---

## 6. 一句话

**图型 agent（4 个）今天的 agentLisp 都能复刻；非图的 2 个（yaoguang / xuanji）不是 DSL 能表达的形状，得先改它们的架构。**
