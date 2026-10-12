# 设计：把 21 个设计模式落到**运行时**

> 结论先行：**编译期已落地（21/21）；运行时落地需要新增一层「模式运行时」。**
> 设计要点：产物已带 `self.PATTERNS`（无需改编译期）→ 运行时新增 `runtime/patterns/` 一层
> （kind → handler）→ 每个 kind 一条**可观测行为**测试 + 一条**反证**测试 → 新判据 A11 机器拦。
> 本设计不改 C1 冻结文件。

## 1. 目标与「落地」的判定标准

一个 kind 算「运行时落地」，当且仅当**同时**满足 3 条（可测）：

1. **行为可观测**：带该模式的 agent 与不带的 agent，在运行时**行为不同**（顺序/拦截/挂起/预算/落盘…）。
2. **由声明驱动**：删掉 `:pattern` 后行为**回到基线**（反证测试，防「碰巧生效」）。
3. **有测试**：`tests/patterns_runtime/` 下有一条用例，断言上述差异。

## 2. 现状（实测）

| 层 | 状态 | 证据 |
|---|---|---|
| 编译期 | **已落地 21/21** | 落地清单 rc=0；AST 闸门 48/48 |
| 产物 | **已带语义** | `self.PATTERNS = [{'pattern': "priority", 'markers': [...]}]`（产物第 50 行） |
| 运行时 | **部分/多数未落** | 读 `PATTERNS` 的代码 **0 处**；21 kind 中 13 个在 runtime/ 命中 **0** |

## 3. 架构（5 层，单向依赖）

```
.al 源码 ──编译期（已落地）──► 产物：self.PATTERNS / self.EVOLUTION
                                      │
                                      ▼
                          ┌───────────────────────────┐
                          │ L1 载入层 PatternRuntime   │  读 self.PATTERNS，解析+校验
                          ├───────────────────────────┤
                          │ L2 注册表层 HANDLERS       │  kind → PatternHandler（唯一映射）
                          ├───────────────────────────┤
                          │ L3 行为层 Handler.execute  │  挂钩 constrain/verify/build_context/tracer
                          ├───────────────────────────┤
                          │ L4 组合层 顺序与冲突       │  多模式共存：声明顺序 + 显式优先级
                          ├───────────────────────────┤
                          │ L5 观测层 trace/span       │  每次介入写 trace，便于评审与断言
                          └───────────────────────────┘
```

## 4. 契约与接口

```python
# runtime/patterns/__init__.py
class PatternHandler(Protocol):
    kind: str
    def on_init(self, h: Any) -> None: ...            # 载入时一次性（可拒绝不合法的组合）
    def before_turn(self, h: Any, ctx: dict) -> dict: ...   # 改上下文/选工具
    def on_tool_call(self, h: Any, call: dict) -> tuple[bool, str]: ...  # 拦截（复用 constrain）
    def after_turn(self, h: Any, ctx: dict) -> dict: ...    # 校验/重试/落盘

HANDLERS: dict[str, PatternHandler] = {...}   # 唯一映射（与编译期 21 kind 对齐）
def load(harness: Any) -> list[PatternHandler]: ...   # 读 harness.PATTERNS → 实例化
```

规则（可测）：

| 规则 | 取值 | 理由 |
|---|---|---|
| 载入点 | `BaseHarnessV2.__init__` 末尾调 `patterns.load(self)` | 产物已先赋值 `self.PATTERNS`，无需改编译期（不改 C1） |
| 未知 kind | **启动即报错**（与编译期同口径） | 不许静默降级 |
| 未声明模式 | 不载入任何 handler，行为与今天完全一致 | 向后兼容（由现有 356 用例守护） |
| 多模式顺序 | 按产物中的**声明顺序**；同一钩子内串行 | 确定性 |
| 冲突 | `on_init` 内检测，冲突即报错并给出双方 kind | 不许沉默 |

## 5. 21 个 kind 的运行时落点（每行 = 一条可观测断言）

| # | kind | 官方语义（注册表） | 运行时落点 | 可观测断言 | 批 |
|---|---|---|---|---|---|
| 1 | reflect | 失败进反思—修正回路 | after_turn 触发复核 | 失败一次后出现 reflect 步 + 二次尝试用了复核意见 | 1 |
| 2 | router | 先判意图再分发 | before_turn 选 worker | 两种输入走不同 worker | 2 |
| 3 | chain | 顺序步骤，前步输出注入后步 | before_turn 串行推进 | 步骤顺序 + 上下文含上步输出 | 2 |
| 4 | parallel | 分支并行，最后归并 | 并发调用 + 归并 | 并发度 > 1 且结果合并 | 2 |
| 5 | planner | 先计划再执行，末轮报完成度 | 首轮 plan + 末轮 report | trajectory 含 plan 与完成度 | 2 |
| 6 | **priority** | 按 criteria 排序，levels 分层 | build_context/工具选择排序 | 出队顺序符合 criteria（**首个切片**） | 2 |
| 7 | decomposition | 递归分解，max-depth 限层 | 生成子任务树 | 子任务层级 = max-depth | 2 |
| 8 | fsm | initial-state + states | 状态迁移校验 | 非法迁移被拒 | 2 |
| 9 | evaluator | 双阈值 | verify 后按阈值分流 | 阈值边界行为正确 | 1 |
| 10 | topic-model | processor 子 agent 聚类 | 调用 processor | processor 被调用 + 主题数 | 3 |
| 11 | decomposer | schema-fields 类型检查 | 结构化提取校验 | 字段类型错被拒 | 2 |
| 12 | guardrails-safety | 三段钩子 | 入/出/审计三钩 | 违规输入或输出被拦 | 1 |
| 13 | hitl | approval-before 阶段 | 挂起等 signal | 挂起 + 批准后继续 | 1 |
| 14 | exception | retries + backoff | 包装工具/模型调用 | 失败 N 次后按策略 | 1 |
| 15 | exploration | budget + convergence | 预算计数与收敛停止 | 超预算即停 | 2 |
| 16 | rag | 先检索后生成，证据回填 | 检索前置 + 引用校验 | 回答含证据 id | 1 |
| 17 | a2a | 跨 agent 通信 | agent card + 消息总线 | 消息往返成功 | 3 |
| 18 | reasoning | CoT / 树状探索 | prompt 与解析 | 推理结构出现在 trajectory | 1 |
| 19 | learning | 反馈写回技能层 | 落盘 | 落盘文件 + 下次生效 | 3 |
| 20 | resource-aware | 按成本/时延选档 | 模型选择器 | 低预算走低档 | 2 |
| 21 | goal-setting | 目标/进度/偏差 | 目标登记 + 偏差检测 | 偏差触发处理 | 2 |

## 6. 验收与门禁

| 项 | 内容 |
|---|---|
| 每 kind | `tests/patterns_runtime/test_<kind>.py`：行为差异 1 条 + 反证（去掉 `:pattern` 回基线）1 条 |
| 向后兼容 | 现有 **356** 用例必须保持全绿（未声明模式 → 行为不变） |
| 新判据 **A11** | 21 个 kind 必须都有运行时用例；缺一个即失败（真源 `tools/test_paths.txt` 已含 `tests`，自动进 CI） |
| CI | ubuntu + windows 双平台（沿用现状） |
| 观测 | 每次 handler 介入写一条 trace（可被断言、可被评审看到） |

## 7. 里程碑（工作量：经验值）

| 批 | 范围 | 交付物 | 工作量（经验值） |
|---|---|---|---|
| **0 切片** | 只做 priority | handler + 2 条测试 + A11 骨架 | 2–4 小时 |
| 1 接线 | reflect/evaluator/guardrails-safety/hitl/exception/rag/reasoning | 7 kind 落地 | 1–2 工程日 |
| 2 轻量新增 | router/chain/parallel/planner/priority/decomposition/fsm/decomposer/exploration/resource-aware/goal-setting | 11 kind 落地 | 4–8 工程日 |
| 3 外部依赖 | topic-model/a2a/learning | 3 kind 落地（含依赖接入） | 3–6 工程日 |

## 8. 风险与代价（明示）

| 风险 | 说明 | 对策 |
|---|---|---|
| **意图歧义** | 上述落点是我按注册表一句话语义的**推断**，可能与原作者意图不同 | 每 kind 的断言先给专家确认口径，再实现（评审包第 8 节问题 2 已提出） |
| 行为回归 | 接线后可能改变既有 agent 行为 | 未声明模式不载入 handler；356 用例守护；A11 门禁 |
| 性能 | 每轮多几次 Python 调用（**经验值**：可忽略） | 只在声明了模式时载入；hook 内不做 IO 除非该 kind 需要 |
| 批 3 依赖 | a2a/learning/topic-model 需外部服务或模型能力 | 单独排期，可用 Null 实现 + 显式告警 |

## 9. 明确不做（边界）

1. 不改编译期口径（21 kind、键集合、emit 形状保持不变）。
2. 不动 C1 冻结文件；产物已有的 `self.PATTERNS` 足以支撑载入。
3. 不让模式「自动决策」：本设计只做**确定性、可断言**的行为；引入模型判断的部分（如 router 的意图判定）复用既有 LLM 调用，不新增隐式行为。
4. 不为未落地 kind 伪造「已落地」标记：A11 未通过就是未通过。
