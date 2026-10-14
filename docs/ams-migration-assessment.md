# AMS 能力可迁移性评估（实测）

> 问题：AMS 的能力搬进 agentLisp 后，AMS 能不能废除？
> 方法：取 AMS **生产在用**的 spec（`examples/tianji/spec.yaml`）逐构造对照 agentLisp 语言能力，
>      并对能表达的部分真跑编译器（不是桌面推演）。
> 日期：2026-10-14 · 对应提交 `cbd1b42`

---

## 一、结论

**可迁移，但不是翻译，是重新设计。** 结论分三段：

1. **运行时零耦合** —— AMS 生成的两个星不 import AMS。抽掉 AMS 仓库，它们照跑。
2. **再生成做不到** —— tianji 的 7 个构造里，agentLisp 现在只能声明 1 个。
3. **所以：保留 AMS 为工具，不在产品链路。** 不删仓库，不再新增提交。

---

## 二、运行时耦合实测

| 检查 | 结果 | 证据 |
|---|---|---|
| `beidou/tianji/agent.py` 是否 import AMS | 否 | 仅 `asyncio/re/langgraph/openai/typing_extensions` |
| `beidou/yaoguang/agent.py` 是否 import AMS | 否 | 仅 `openai` + 同目录 `prompt_assembler`/`tools` |
| beidou 是否依赖 AMS 包 | 否 | `pyproject.toml`/`requirements.txt` 无 `ams` |
| 谁 import `agent-plugin-protocol` | 无外部消费者 | 仅 AMS 自身 + `shared/docs` 文档 |

**含义**：AMS 只在「再生成一次」时需要。产物是自包含资产。

---

## 三、逐构造对照（tianji spec vs agentLisp）

| # | tianji 用的构造 | agentLisp 现状 | 判定 |
|---|---|---|---|
| 1 | `workflow.nodes` 7 节点 + `topology: sequential` | 无 workflow/transition；`:multiagent :topology` 只收 `peer/orchestration/decentralised/judge-driven` | ❌ 不可直接表达 |
| 2 | 3 个 `type: computation` 节点 + `handler: my_handlers.x` | `:tools` 有 `define-tool`，但只声明 I/O 签名，无实现映射 | ❌ 需外部约定 |
| 3 | `state.fields` 14 个具名字段 + 类型 + 默认值 | 无声明状态构造（状态在 Harness 内部） | ❌ 缺 |
| 4 | agent 节点 prompt 里的 `{metrics_summary}` 插值 | prompt 里可写文本；无语言级插值 | ⚠️ 靠运行时约定 |
| 5 | `model.provider: deepseek-official` | `PROVIDER-ENUM = (anthropic openai qwen mock)` | ❌ 编译期被拒（exit 2，实测） |
| 6 | `tools[].type: computation` + `permission: read` | 无对应字段 | ❌ 缺 |
| 7 | `evaluation.metrics[].threshold: "<85"` | 无阈值门构造 | ❌ 缺 |

### 真跑结果

| 尝试 | 命令 | 退出码 | 说明 |
|---|---|---|---|
| 逐构造直写（7 节点塞进 `:system-prompt`） | `racket compiler/main.rkt -i /tmp/tianji_attempt.al -o ...` | 0 | 编译通过，但 7 节点语义**全在 prompt 文本里**，不是结构 |
| 用 `defmultiagent` 表达 7 节点 | 同上 | 0 | 产物含 7 个 worker + `topology: orchestration`；`sequential` 会被拒 |
| provider 用 `deepseek-official` | `--check-only` | 2 | `:provider 枚举=(anthropic openai qwen mock)` |

**能活下来的**：7 个 worker 的名字与模型配置、模式声明（`self.PATTERNS`）。
**活不下来的**：节点类型、执行顺序、状态字段、handler 接线、输出字段映射。

---

## 四、共享判据表（两边共用，禁止各写一份）

| 构造 | AMS | agentLisp |
|---|---|---|
| 载体 | YAML `spec.yaml` | S-表达式 `.al` |
| 执行顺序 | `workflow.topology` 声明式 DAG | 无；顺序写在 prompt 或由 `:multiagent` 拓扑决定 |
| 状态 | `state.fields` 声明 | 无声明；Harness 内部 |
| 确定性步骤 | `type: computation` + `handler` 接线 | 无；只能作 tool 描述 |
| 节点级 prompt | 每节点独立 `prompt` + `{}` 插值 | 单个 `:system-prompt`，无插值 |
| 产物目标 | langgraph / crewai / autogen / native / skills-agent | 仅 `BaseHarnessV2` |
| 覆盖保护 | ❌ 无（有人写了 7 条断言手守） | ✅ 内嵌 sha256 + 拒绝覆盖 + `--force` |

---

## 五、决定与绑定点

**建议决定**：AMS 降级为设计期工具箱。不进产品链路，不再新增提交。

**代价（必须告知）**：tianji 要改行为时，agentLisp 目前替代不了。两条路：

| 路 | 做法 | 代价 |
|---|---|---|
| A | 手工改 `beidou/tianji/agent.py` | 放弃从 spec 再生成；改动不可复现 |
| B | 在 agentLisp 补构造 1/2/3 | 先补 workflow DAG + 确定性节点 + 状态声明，再迁 |

**绑定点**：tianji 的执行模型能否从「sequential DAG」改成「orchestration 拓扑」。
这是语义变更，不是语法迁移。**需要你拍。**

---

## 六、验证记录（2026-10-14 实跑）

| 命令 | 结果 |
|---|---|
| `export PATH=$PWD/.racket/bin:$PATH && python3 -m pytest tests/ -q --no-cov` | **532 passed, 5 skipped**（SRS 锚为 146；本轮 drift 新增 6 条） |
| `python3 -m pytest -q --no-cov`（全仓） | 423 passed, 212 skipped |
| `python3 tools/standards_check.py` | 17/17 通过（改动前为 12 通过 / 4 跳过） |
| `ruff check .` / `ruff format --check` | All checks passed / 82 files already formatted |

> 差异说明：全仓 423 < `tests/` 子集 532，因两次运行的**选择集不同**（全仓含 `runtime/tests`、
> `python/tests` 等，且各自带 skip）。两个数不可互推。

## 七、未验证

- 本文只逐构造对照了 **tianji** 一份 spec。yaoguang（skills-agent 变体）与 3 个 `dist` 未测。
- 「补构造 1/2/3 的工时」是经验值，未估算依据。
- tianji 与 yaoguang 里手工补丁的完整清单未核（`tianji/AGENT_SKELETON_PATCHES.md` 只读了开头）。
- AMS 1167 测试全绿，但其 `docs/architecture-review.md` 自认 spec→IR 有接线断层，
  测试数不能当能力上限。
