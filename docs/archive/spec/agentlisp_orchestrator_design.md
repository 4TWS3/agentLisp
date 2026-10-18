# 设计：编排调度器（让 router / chain / parallel / planner / decomposition 真生效）

> 结论先行：这 5 个 kind 现在只做**指令注入**，引擎不执行 ✗。
> 本设计新增一层 `runtime/orchestrator.py`：把 ReAct 循环的「下一动作」交给编排器决定 ✓。
> 不改编译期口径 ✓；未声明编排模式时走原循环（向后兼容 ✓）。

## 1. 目标与判定标准

| # | 判据 | 怎么测 |
|---|---|---|
| 1 | 编排行为可观测 | trace/turns 里出现步骤名、worker 名、并发度、计划与完成度 |
| 2 | 由声明驱动 | 删掉 `:pattern` 后行为回基线（反证） |
| 3 | 确定性 | 同一状态 + 同一输入 → 同一决策（可断言） |
| 4 | 有契约 | 每 kind 一份契约 + 运行时测试（沿用 A11） |

## 2. 现状与缺口（实测）

| 事实 | 证据 |
|---|---|
| handler 已有纯函数：`route` / `steps` + `next_step` / `branches` + `fan_in` / `plan_size` + `completion` / `children` | runtime/patterns/declarative_b2.py |
| 引擎**没有**调度点：ReAct 循环自己决定下一步 | runtime/base_harness_v2.py 的主循环 |
| 引擎**没有**子 agent / 并发原语 | 无 `spawn` / `gather` 于 runtime/ |
| 5 个 kind 当前只有指令注入 | 与资源感知等 13 个已接线的对比可见 |

## 3. 架构（在既有 5 层上加一层）

```
产物 self.PATTERNS
   │
   ▼
PatternRuntime（已有：载入/冲突/钩子/观测）
   │
   ▼
Orchestrator（新）：select_next(state) -> Action     ← 唯一决策点
   │
   ├── step(ctx)                  ：普通一步（可注入提示）
   ├── spawn(worker, task)        ：拉起子 agent（router / decomposition）
   ├── fanout(branches)           ：并发分支 + fan_in 归并（parallel）
   └── finish(report)             ：结束并报完成度（planner）
```

**唯一决策点**：`step()` 前调用 `orchestrator.select_next(state)` ✓。
未声明编排模式 → 返回 `step(ctx)`（与今天完全一致 ✓）。

## 4. 五个 kind 的执行语义（每行一条可观测断言）

| kind | 依据的纯函数 | 执行语义 | 可观测断言 | 批 |
|---|---|---|---|---|
| chain | `steps` + `next_step(i)` | 按顺序推进步骤，前一步输出注入下一步上下文 | turns 里的步骤名序列 == steps | 1 |
| planner | `plan_size` + `completion` | 首轮输出计划（长度 plan-size）；末轮报完成度 | trace 含 plan 与 completion | 1 |
| router | `route(intent)` | 判定意图后 `spawn` 对应 worker | trace 的 worker 字段 == routes 映射 | 2 |
| parallel | `branches` + `fan_in` | 分支并发拉起，最后归并 | 并发度 > 1 且结果数 == 分支数 | 2 |
| decomposition | `children(task, depth)` | 递归生成子任务，深度受 max-depth 限制 | 子任务层级 == max-depth | 3 |

## 5. 接口（新）

```python
class Action(Protocol):
    kind: str            # step | spawn | fanout | finish
    worker: str | None
    task: str | None
    branches: list[str]

class Orchestrator(Protocol):
    def select_next(self, state: dict) -> Action: ...
```

规则：决策只看 `state`（步数、已完成步骤、已用预算）；禁止读时间/随机数 ✓（保证判据 3 ✓）。

## 6. 端口

| 端口 | Mock（测试用） | 用途 |
|---|---|---|
| Clock | FakeClock（手动推进） | 并发与退避计时 |
| WorkerFactory | StubWorker（返回确定结果） | spawn 子 agent |
| Tracer | 内存记录 / OTel | 观测（已有 ✓） |

## 7. 验收

| 项 | 内容 |
|---|---|
| 每 kind | 契约 1 份 + 行为测试 1 条 + 反证 1 条（沿用 A11 ✓） |
| 组合 | 编排组内互斥（已有 ✓）+ 与 13 个已接线 kind 的组合仍按声明顺序 ✓ |
| 回归 | 现有 633 用例必须全绿 ✓（未声明编排模式 → 行为不变 ✓） |
| 观测 | 每个 Action 写一条事件（已有 `_record` ✓） |

## 8. 里程碑（工作量：经验值）

| 批 | 范围 | 交付 | 工作量（经验值） |
|---|---|---|---|
| 1 | chain + planner（顺序类，最简） | orchestrator + 2 契约 + 4 测试 | 1–2 工程日 |
| 2 | router + parallel（需要 spawn / 并发 + 假时钟） | WorkerFactory + 4 测试 | 2–3 工程日 |
| 3 | decomposition（递归 + 深度限制） | 子任务树 + 4 测试 | 2–4 工程日 |

## 9. 风险与代价

| 风险 | 对策 |
|---|---|
| 并发不确定性 | 决策不读时间/随机 ✓；并发用假时钟 + 确定性归并顺序 ✓ |
| token 成本上升 | 子任务数受 max-depth 与 plan-size 限制 ✓（编译期键已有 ✓） |
| 向后兼容 | 未声明编排模式 → 走原循环 ✓；633 用例守护 ✓ |
| 复杂度扩散 | 唯一决策点 ✓；编排逻辑不散落到 handler ✓ |

## 10. 明确不做

1. 不改编译期口径（21 kind、键集合、emit 形状不变 ✓）。
2. 不做跨进程/跨网络的真实子 agent（本设计只做进程内 ✓）。
3. 不做自动重规划（失败重试仍由 exception 模式负责 ✓）。
