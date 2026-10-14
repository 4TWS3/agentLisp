# 观察值键（用户可见说明）

> 用途：读 trace、写模式时，知道 `verify(observation)` 会读哪些键。
> 唯一真源：`runtime/` 里 `observation.get(...)` / `observation[...]` 的**实际读取点**。
> 机器核对：`python3 scripts/check_observation_keys_doc.py`（本表缺键即 rc=1）。
> 来源：US-24 / 主计划 P2-6。

---

## 1. 键总表

工具结果键（4 个）：

| 键 | 谁读 | 含义 | 缺省行为 |
|---|---|---|---|
| `exit_code` | `BaseHarnessV2.verify` | 工具退出码 | 缺省按 0 处理（视为通过） |
| `stdout` | `BaseHarnessV2` 轨迹记录 | 工具标准输出 | 缺省空串 |
| `stderr` | `BaseHarnessV2.verify` | 工具标准错误 | 与 `error` 二选一，作失败原因 |
| `error` | `BaseHarnessV2.verify` | 失败原因文本 | 与 `stderr` 二选一 |

模式观察门键（10 个键名，含 2 个别名）：

| 键 | 谁读（kind） | 含义 | 缺省行为 |
|---|---|---|---|
| `answer` | rag | 最终答案文本 | 与 `final_answer` 二选一 |
| `final_answer` | rag | `answer` 的别名 | 与 `answer` 二选一 |
| `evidence_ids` | rag | 证据 id 列表 | 空列表；rag 下无证据即拦 |
| `fields` | decomposer | 结构化字段 | 与 `payload` 二选一 |
| `payload` | decomposer | `fields` 的别名 | 与 `fields` 二选一 |
| `score` | evaluator | 候选评分 | 无该键则跳过阈值判定 |
| `reviewer` | reflect | 复核结论 | reflect 下为假即拦 |
| `audit` | guardrails-safety | 审计记录 | guardrails-safety 下为假即拦 |
| `reasoning` | reasoning | 显式推理结构 | reasoning 下为假即拦 |
| `progress` | goal-setting | 目标进度 | 无该键则跳过偏差判定 |

**合计 14 个键名**（12 个概念 + 2 个别名）。

---

## 2. 两个来源，不要混

| 来源 | 键 | 何时出现 |
|---|---|---|
| 工具结果 | `exit_code` / `stdout` / `stderr` / `error` | 每次工具调用后 |
| 模式观察门 | 其余 | 模式 handler 需要时 |

---

## 3. 常见误读

1. `answer` 与 `final_answer` 等价。代码**优先**读 `answer`。
2. `fields` 与 `payload` 等价。代码**优先**读 `fields`。
3. `score` 缺省**不是** 0。没有该键就跳过 evaluator 阈值判定。
4. `stderr` 与 `error` 都是失败原因。代码优先读 `stderr`。
