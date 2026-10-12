# 设计：把 21 个设计模式落到**运行时**（v2 · 已采纳评审意见）

> 结论先行：编译期已落地 21/21；运行时落地新增一层「模式运行时」。
> **v2 变更（回应评审 3 条）**：
> ① 语义偏差 → **行为契约先冻结**（§5，契约文件 + A11 判据）；编码前必须过契约评审。
> ② 组合冲突 → **显式冲突矩阵**（§6，分组 + 顺序规则 + 21×21 组合测试）。
> ③ 外部依赖 → **端口 + Mock 驱动分批**（§7，批 3 先用内存实现交付，Null 适配器必须显式告警）。
> 本设计不改 C1 冻结文件。

## 1. 目标与「落地」判定标准

| # | 判据 | 怎么测 |
|---|---|---|
| 1 | 行为可观测 | 带模式 vs 不带，运行时行为不同 |
| 2 | 由声明驱动 | 删掉 `:pattern` 后行为回基线（反证） |
| 3 | 有测试 | `tests/patterns_runtime/test_<kind>.py` 存在且通过 |
| 4 | **契约已冻结** | 该 kind 的契约文件（§5）存在，且测试断言的 id 与契约一致 |

## 2. 现状（实测）

| 层 | 状态 | 证据 |
|---|---|---|
| 编译期 | 已落地 21/21 | 落地清单 rc=0；AST 闸门 48/48 |
| 产物 | 已带语义 | `self.PATTERNS = [{'pattern': "priority", ...}]` |
| 运行时 | 部分/多数未落 | 读 `PATTERNS` 的代码 0 处；21 kind 中 13 个在 runtime/ 命中 0 |

## 3. 架构（5 层，单向依赖）

```
.al 源码 ──编译期（已落地）──► 产物：self.PATTERNS / self.EVOLUTION
                                      │
                                      ▼
  L1 载入层  PatternRuntime     读 self.PATTERNS，解析 + 校验（未知 kind 报错）
  L2 注册层  HANDLERS           kind → PatternHandler（唯一映射，与编译期 21 kind 对齐）
  L3 行为层  Handler.execute     挂钩 constrain / verify / build_context / tracer
  L4 组合层  ConflictPolicy     声明顺序 + 分组互斥 + 冲突即报错（§6）
  L5 观测层  trace/span         每次介入写一条 trace（可断言、可评审）
```

## 4. 契约与接口

```python
class PatternHandler(Protocol):
    kind: str
    def on_init(self, h: Any, others: list[str]) -> None: ...   # 组合校验（§6）
    def before_turn(self, h: Any, ctx: dict) -> dict: ...
    def on_tool_call(self, h: Any, call: dict) -> tuple[bool, str]: ...
    def after_turn(self, h: Any, ctx: dict) -> dict: ...

HANDLERS: dict[str, PatternHandler] = {...}
def load(harness: Any) -> list[PatternHandler]: ...   # 读 harness.PATTERNS → 实例化 + 冲突校验
```

| 规则 | 取值 | 理由 |
|---|---|---|
| 载入点 | `BaseHarnessV2.__init__` 末尾 | 产物已先赋值 `self.PATTERNS` → 不改编译期 |
| 未知 kind | 启动即报错 | 与编译期同口径，不许静默降级 |
| 未声明模式 | 不载入 handler，行为与今天一致 | 向后兼容（356 用例守护） |

## 5. 【评审建议 ①】行为契约先冻结（编码前）

**做法**：每个 kind 先写**契约**（不含实现），评审通过后才写代码。契约是唯一口径来源。

**契约文件**：`docs/spec/pattern_runtime_contracts/<kind>.md`（21 份），每份固定 6 栏：

| 栏 | 内容 | 例（priority） |
|---|---|---|
| id | 契约 id（测试断言引用它） | `CT-PRIORITY-01` |
| 输入 | 触发场景（.al 片段 + 运行时输入） | 3 个候选动作 + criteria=urgency |
| 期望 | **可观测**行为（顺序/拦截/挂起/预算/落盘） | 出队顺序 = urgency 降序 |
| 反证 | 去掉 `:pattern` 后的基线 | 顺序 = 声明顺序 |
| 端口 | 需要的外部能力（无则 None） | None |
| 不可观测项 | 明确不承诺的东西 | 不承诺模型内部打分过程 |

**冻结流程（每 kind 5 步，缺一步不算落地）**：

```
1 写契约 → 2 专家确认（或按 §8 默认口径）→ 3 写失败测试(红) → 4 实现(绿) → 5 门禁
```

**机器拦（A11 扩展）**：21 个 kind 每个都必须有 (a) 契约文件、(b) 运行时测试、
(c) 测试里引用该契约 id。缺任一即失败。

## 6. 【评审建议 ②】组合冲突显式化

**分组**（同组内**只能选一个**；跨组可共存）：

| 组 | 成员 | 互斥理由 |
|---|---|---|
| 编排 | chain / parallel / planner / router | 同一轮只能有一种执行编排 |
| 状态 | fsm / goal-setting | 两套状态跟踪会互相覆盖 |
| 评估 | evaluator / decomposer | 都在 verify 后改判定 |
| 质量 | reflect / exception | 失败处理回路重叠 |
| 安全 | guardrails-safety / hitl | 都可挂起/拦截 |
| 知识 | rag / topic-model / learning | 都改写上下文来源 |
| 资源 | resource-aware / exploration | 都按预算裁剪行为 |
| 协作 | a2a / decomposition | 都产生子任务/子 agent |

**顺序规则**：跨组按**声明顺序**串行；同钩子内确定性（不依赖 dict 顺序）。
**冲突即报错**：`on_init` 检出同组多成员 → 抛错并**点名双方 kind** 与所属组。

**组合测试**：`tests/patterns_runtime/test_conflict_matrix.py` 枚举 **21×21 = 441** 对：

| 组合类型 | 期望 |
|---|---|
| 同组两成员 | 启动失败，错误信息含两个 kind 名 |
| 跨组两成员 | 启动成功；钩子顺序 == 声明顺序 |
| 同一 kind ×2 | 幂等（只载一个）或显式报错（二选一，测试固定） |

## 7. 【评审建议 ③】端口 + Mock 驱动分批交付

| 端口 | Mock（测试用） | 生产适配器（后置） | 用它的 kind |
|---|---|---|---|
| `Retriever` | `InMemoryRetriever`（夹具语料） | 向量库/HTTP | rag、topic-model |
| `MessageBus` | `InMemoryBus` | HTTP/gRPC/队列 | a2a |
| `SkillStore` | `InMemorySkillStore` | 文件/DB | learning |
| `ModelRouter` | `StubRouter`（按成本表返回档位） | 真实计费/延迟表 | resource-aware |
| `Clock` / `Tracer` | 假时钟 / 内存 tracer | 真实 | 所有 |

**硬规则**：Null/Mock 适配器必须**显式告警**（日志 + trace 标记 `adapter=mock`）✓；
CI 只在 Mock 下跑 ✓；生产适配器另开批次 ✓。

## 8. 21 个 kind 的落点（每行一条可观测断言）

| # | kind | 运行时落点 | 可观测断言 | 批 | 端口 |
|---|---|---|---|---|---|
| 1 | reflect | after_turn 触发复核并重试 | 失败一次后出现 reflect 步，二次尝试用了复核意见 | 1 | Clock |
| 2 | router | before_turn 选 worker | 两种输入走不同 worker | 2 | — |
| 3 | chain | before_turn 串行推进 | 步骤顺序 + 上下文含上步输出 | 2 | — |
| 4 | parallel | 并发分支 + 归并 | 并发度 > 1 且结果合并 | 2 | — |
| 5 | planner | 首轮 plan + 末轮报告 | trajectory 含 plan 与完成度 | 2 | — |
| 6 | **priority** | 候选动作按 criteria 排序 | 出队顺序 = criteria 序（**首个切片**） | 2 | — |
| 7 | decomposition | 生成子任务树 | 层级 = max-depth | 2 | — |
| 8 | fsm | 状态迁移校验 | 非法迁移被拒 | 2 | — |
| 9 | evaluator | verify 后按双阈值分流 | 阈值边界行为正确 | 1 | — |
| 10 | topic-model | 调 processor 聚类 | processor 被调用 + 主题数 | 3 | Retriever |
| 11 | decomposer | schema-fields 校验 | 字段类型错被拒 | 2 | — |
| 12 | guardrails-safety | 入/出/审计三钩 | 违规输入或输出被拦 | 1 | — |
| 13 | hitl | approval-before 阶段挂起 | 挂起 + 批准后继续 | 1 | Clock |
| 14 | exception | 包装调用 + retries/backoff | 失败 N 次后按策略 | 1 | Clock |
| 15 | exploration | 预算计数 + 收敛停止 | 超预算即停 | 2 | — |
| 16 | rag | 检索前置 + 证据回填 | 回答含证据 id | 1 | Retriever |
| 17 | a2a | agent card + 消息往返 | 消息往返成功 | 3 | MessageBus |
| 18 | reasoning | 显式推理结构 | 推理结构出现在 trajectory | 1 | — |
| 19 | learning | 反馈写回 | 落盘 + 下次生效 | 3 | SkillStore |
| 20 | resource-aware | 按成本/时延选档 | 低预算走低档 | 2 | ModelRouter |
| 21 | goal-setting | 目标登记 + 偏差检测 | 偏差触发处理 | 2 | — |

## 9. 里程碑（工作量：经验值）

| 批 | 范围 | 交付物 | 工作量（经验值） |
|---|---|---|---|
| **0 切片** | priority 全流程（契约→红→绿→门禁） | 契约 1 + 测试 2 + A11 骨架 | 4–6 小时 |
| 1 接线 | reflect/evaluator/guardrails-safety/hitl/exception/rag/reasoning | 7 kind × 5 步 | 2–3 工程日 |
| 2 轻量新增 | router/chain/parallel/planner/priority/decomposition/fsm/decomposer/exploration/resource-aware/goal-setting | 11 kind × 5 步 | 5–9 工程日 |
| 3 Mock 交付 | topic-model/a2a/learning（Mock + 告警） | 3 kind × 5 步；生产适配器另排 | 3–4 工程日 |

## 10. 风险与代价（更新后）

| 风险 | 本版对策 |
|---|---|
| 语义偏差 | 契约先冻结（§5）：测试引用契约 id，口径漂移即失败 |
| 组合冲突 | 冲突矩阵 + 441 组合测试（§6）：冲突报错点名双方；顺序确定性 |
| 外部依赖 | 端口 + Mock（§7）：批 3 无外部服务也能交付；Null 适配器显式告警 |
| 向后兼容 | 未声明模式不载入 handler；356 用例守护；A11 门禁 |
| 性能 | 仅声明模式时载入；hook 内不做 IO（经验值：开销可忽略） |

## 11. 明确不做

1. 不改编译期口径（21 kind、键集合、emit 形状不变）。
2. 不动 C1 冻结文件。
3. 不做「自动决策」：只做确定性、可断言的注入式行为。
4. 不为未落地 kind 伪造标记：A11 未过就是未过。

## 12. 评审意见响应表

| 评审意见 | 落在哪 | 可测形式 |
|---|---|---|
| ① 编码前冻结行为测试口径 | §5 + §1 判据 4 | 契约 21 份 + A11 校验「契约 + 测试 + id 引用」 |
| ② 显式校验 on_init 冲突规则 | §6 | 分组互斥 + 21×21 组合测试（冲突必报错并点名） |
| ③ Mock 驱动分批交付 | §7 + §9 批 3 | 5 个端口 + 内存 Mock + Null 适配器显式告警 |
