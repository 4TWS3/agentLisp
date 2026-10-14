# US-30 交底：槽位模型（F-AMS-6 / 决策 D3）

> 基线：`01aca4d` · 日期：2026-10-14
> 故事：US-30（作为 M，我要槽位模型，以便「声明了却不发生」不可能）
> 判据：LANDED 只收槽位非空的 kind

---

## 1. 结论

槽位模型已落地。**LANDED = 13**（占槽位）；**DECLARED_ONLY = 8**（声明层）。
口径短语改为：**契约 21 / 落地 13 / 声明层 8**。

---

## 2. 决定（用户授权：调研后自行决定）

### 2.1 槽位定义

槽位只算「**引擎按 kind 分派、且改变引擎行为**的调用点」。
通用 base 注入（所有 kind 都有的 before_turn 摘要）**不算**。否则 21 个全非空，模型失去意义。

### 2.2 8 个槽位（7 实现 + 1 待实现）

| 槽位 | 调用点 |
|---|---|
| `on_init` | PatternRuntime._instantiate -> handler.on_init |
| `before_turn` | BaseHarnessV2.build_context |
| `on_tool_call` | BaseHarnessV2.call_tool |
| `verify` | BaseHarnessV2.verify -> verify_observation |
| `evaluate` | verify_observation 的 evaluator 分派 |
| `order` | build_context -> PatternRuntime.order |
| `budget` | retries_cap + turn_budget |
| `orchestrate` | 待实现（F-AMS-7） |

### 2.3 与 D3 的一处差异（有证据）

D3 的 8 个已实现槽位含 `after_turn`。实测：`PatternRuntime.after_turn` **全仓无调用点**
（`grep 'patterns.after_turn'` 零命中）。按 D3 自己的防膨胀规则「槽位只能由运行时调用点定义」，
`after_turn` 不是槽位，已删。故已实现 7 个 + `orchestrate` = **8**（D3 原为 9）。

---

## 3. 每个 kind 的占用

| kind | 槽位 |
|---|---|
| priority | order |
| exception | budget |
| exploration | budget |
| resource-aware | on_init |
| hitl | on_tool_call |
| fsm | on_tool_call |
| rag / decomposer / reflect / guardrails-safety / reasoning / goal-setting | verify |
| evaluator | evaluate、verify |
| a2a / chain / decomposition / learning / parallel / planner / router / topic-model | 无（声明层） |

---

## 4. 交付

| 文件 | 作用 |
|---|---|
| `runtime/patterns/__init__.py` | 唯一真源：SLOTS / KIND_SLOTS / LANDED / DECLARED_ONLY / CONTRACTED |
| `scripts/check_slot_model.py` | 核对：契约集合 / 槽位子集 / 划分 / 调用点 / 契约槽位行 |
| `tests/test_slot_model.py` | 接入门禁 |
| `tools/standards_check.py` A11 | 改为解析 KIND_SLOTS；契约 + 测试对 21 个登记 kind 仍全查 |
| 21 份契约 | 各加一行槽位行 |
| US-42 三处 | 口径短语改为「契约 21 / 落地 13 / 声明层 8」 |

---

## 5. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 槽位模型 | `python3 scripts/check_slot_model.py` | `OK ... CONTRACTED=21 LANDED=13 DECLARED_ONLY=8 SLOTS=8`，rc=0 |
| 口径一致 | `python3 scripts/check_pattern_consistency.py` | `OK 三处口径一致：契约 21 / 落地 13 / 声明层 8`，rc=0 |
| 判据 | `python3 tools/standards_check.py` | 17 通过 / 0 失败；A11 报「21 个登记，13 个占槽位」 |
| 相关测试 | `pytest` 7 个文件 | 19 passed |
| 全仓 | 提交门禁 | 见 §5.1 |

### 5.1 全仓

| 项 | 值 |
|---|---|
| 命令 | 提交门禁（`raco test compiler/tests/` + ruff + `tools/verify_local.sh -q --no-cov`） |
| 结果 | **642 passed, 8 skipped, 0 failed** |
| 耗时 | 173.96s |
| 门禁 | `[gate] 全过` |

---

## 6. 未做 / 代价

| 项 | 说明 |
|---|---|
| 产物声明槽位 | F-AMS-6 说「一个 pattern 在**产物里**声明它占用哪些槽位」。当前唯一真源是 Python，产物 PATTERNS 未带 slots 字段。判据（LANDED 只收占槽位者）不受影响。**待确认是否补。** |
| `PatternRuntime.after_turn` 是死代码 | 未删。删它会动 4 个 handler 的方法签名，超出本故事判据。 |
| 「槽位数 == 调用点数」 | 7 个已实现槽位各有调用点证据；`budget` 覆盖两个调用点。核对脚本按「每槽位至少一个调用点」核，不作字面数量的强等。 |
| US-42 旧短语 | 「落地 21 / 引擎消费 13 / 仅声明 8」被本故事取代。旧 handoff 保留为历史快照。 |
