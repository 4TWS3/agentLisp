# 用户故事 × Skill 映射

> 目的：给 `user-story-map.md` 的 53 条故事各定一个主 skill 与配套 skill。
> 约束：优先选能端到端交付的 skill。
> 基线：`05591eb` · 日期：2026-10-14
> 性质：本表是映射与开工顺序，不是工时估算。

---

## 0. 结论

1. **主 skill 集中为一条：`delivery-pipeline`。** 53 条故事全部以它为主。
2. **为什么**：只有它覆盖「需求实例化 → Feature → 胶水 → 逐场景 TDD → 集成 → 三级重构 → 冒烟 → 审查 → 提交」。其余 skill 只覆盖其中一个阶段。
3. **其余 skill 作配套。** 它们由主 skill 在对应阶段调用，不替代主 skill。
4. **9 条不能靠 delivery-pipeline 独任。** 原因见 §5。它们仍需主 skill 推进，但判据含库外前提。
5. **`sbe-workflow` / `tdd-workflow` / `feature-dev-workflow` 是 `delivery-pipeline` 的内嵌阶段。** 3 条不单列为主 skill。

---

## 1. 本仓库可用的 skill（筛后）

去掉与本仓库无关的 skill（前端 / Office / 极客时间 / OA / 禅道 / Git 同步 / 环境迁移）。

| skill | 定位 | 在流水线里的位置 |
|---|---|---|
| **`delivery-pipeline`** | **主 skill。** 端到端 9 阶段 | 全流程 |
| `sbe-workflow` | 实例化需求 7 步 | Stage 1（内嵌） |
| `tdd-workflow` | 红→绿→重构微观循环 | Stage 4（内嵌） |
| `feature-dev-workflow` | 老鸟开发工作流 | 与主 skill 重叠，作备选 |
| `refactor` | 坏味道扫描 + 机械修复 | Stage 4 / 5.5 / 6.5 |
| `code-review` | 三层审查：合同→架构→边界 | Stage 6.8 |
| `docker-guard` | Docker + 容器就绪 | Stage 5 / 6 前置 |
| `smart-domain-modeler` | 领域建模（Root/Child/Ref） | 槽位模型与 kind 定性 |
| `task-breakdown` | 大需求拆原子操作 | Stage 1 前的拆解 |
| `local-refactor` | 机械任务外派本地模型 | 大范围改名/改签名 |

---

## 2. 故事 × skill 主表

`配套` 列的 `（内嵌）` 表示该 skill 是主 skill 的固定阶段，不是额外选择。

| 故事 | 阶段 | 故事要点 | 主 skill | 配套 skill | 端到端 |
|---|---|---|---|---|---|
| US-01 | 安装 | pip install / TestPyPI | delivery-pipeline | — | 可 |
| US-02 | 安装 | PyPI 正式发布 | delivery-pipeline | — | **部分** |
| US-03 | 安装 | 独立开发容器 | delivery-pipeline | docker-guard | 可 |
| US-04 | 创作 | 声明状态字段 | delivery-pipeline | sbe-workflow（内嵌） | 可 |
| US-05 | 创作 | 声明工作流图 | delivery-pipeline | — | 可 |
| US-06 | 创作 | defmultiagent 短写法 | delivery-pipeline | — | 可 |
| US-07 | 创作 | 确定性节点 | delivery-pipeline | — | 可 |
| US-08 | 创作 | 节点级提示插值 | delivery-pipeline | — | 可（先断言后实现） |
| US-09 | 编译校验 | 非法工作流编译期拒 | delivery-pipeline | — | 可 |
| US-10 | 编译校验 | 状态字段可达性 | delivery-pipeline | — | 可 |
| US-11 | 编译校验 | 模式组合错误编译期拒 | delivery-pipeline | — | 可 |
| US-12 | 编译校验 | 21 份契约机器校验 | delivery-pipeline | code-review | 可 |
| US-13 | 运行 | 产物不被误改 | — | — | 已完成 |
| US-14 | 运行 | 模式异常不拖垮 Agent | delivery-pipeline | — | 可 |
| US-15 | 运行 | 工具调用被拦截 | delivery-pipeline | — | 可 |
| US-16 | 运行 | 输出文本被校验 | delivery-pipeline | — | 可 |
| US-17 | 运行 | 人工审批生效 | delivery-pipeline | — | 可 |
| US-18 | 运行 | 证据引用被校验 | delivery-pipeline | — | 可 |
| US-19 | 运行 | 编排调度 | delivery-pipeline | docker-guard | 可 |
| US-20 | 运行 | 工具排序 | — | — | 已完成 |
| US-21 | 观测 | 学习条目可写 | delivery-pipeline | — | 可 |
| US-22 | 观测 | 主题分布可观测 | delivery-pipeline | — | 可 |
| US-23 | 观测 | 通信日志可观测 | delivery-pipeline | — | 可 |
| US-24 | 观测 | 观察值键有文档 | delivery-pipeline | — | **部分** |
| US-25 | 观测 | 产物漂移可查 | — | — | 已完成 |
| US-26 | 验证 | 8 个仅声明 kind 接线 | delivery-pipeline | smart-domain-modeler、refactor | 可 |
| US-27 | 验证 | 21 条 E2E | delivery-pipeline | tdd-workflow（内嵌） | 可 |
| US-28 | 验证 | 2 个孤儿条目收口 | delivery-pipeline | smart-domain-modeler | 可 |
| US-29 | 验证 | 真实环境验收 | delivery-pipeline | docker-guard | **受阻** |
| US-30 | 维护 | 槽位模型 | delivery-pipeline | smart-domain-modeler、refactor | 可 |
| US-31 | 维护 | 防膨胀规则 | delivery-pipeline | refactor | 可 |
| US-32 | 维护 | 注册表无悬空 | delivery-pipeline | — | 可 |
| US-33 | 维护 | 契约栏位被机器拦 | delivery-pipeline | code-review | 可 |
| US-34 | 维护 | 模式定义只用声明式 | delivery-pipeline | refactor | 可 |
| US-35 | 维护 | 提交门禁 | delivery-pipeline | — | 可 |
| US-36 | 维护 | kind 计数断言 | — | — | 已存在 |
| US-37 | 发布 | v2.3.1 打补丁 | delivery-pipeline | — | 可 |
| US-38 | 发布 | Release 工作流绿 | delivery-pipeline | — | **部分** |
| US-39 | 发布 | C1 冻结文件追认 | delivery-pipeline | — | **部分** |
| US-40 | 发布 | 接入开销有数 | delivery-pipeline | — | **部分** |
| US-41 | 发布 | 长跑稳定有数 | delivery-pipeline | — | **部分** |
| US-42 | 审计 | 口径三处一致 | delivery-pipeline | code-review | 可 |
| US-43 | 审计 | 证据链能定位首错 | delivery-pipeline | — | 可 |
| US-44 | 审计 | 真实数据集可跑 | delivery-pipeline | — | **受阻** |
| US-45 | 审计 | 评测判据有落点 | delivery-pipeline | — | 可 |
| US-46 | 审计 | :evolution 契约可读 | delivery-pipeline | — | 可 |
| US-47 | 审计 | RSI 规格与实现一致 | delivery-pipeline | code-review | 可 |
| US-48 | 审计 | 在线循环只读 | delivery-pipeline | — | 可 |
| US-49 | 审计 | 离线循环生成补丁 | delivery-pipeline | — | 可 |
| US-50 | 审计 | 隔离验证与清理 | delivery-pipeline | — | 可 |
| US-51 | 审计 | 双集验证 + McNemar | delivery-pipeline | — | 可（依赖 US-44） |
| US-52 | 审计 | 自动提 PR 但人工批准 | delivery-pipeline | — | **受阻** |
| US-53 | 运行 | 节点声明效应等级 | delivery-pipeline | smart-domain-modeler | 可 |

**计数**：可 = 41，部分 = 6，受阻 = 3，已完成 = 3。

---

## 3. 为什么 `delivery-pipeline` 是主 skill

| 理由 | 说明 |
|---|---|
| 覆盖最全 | 从 SBE 到 commit，9 个阶段不缺件 |
| 内嵌其余 skill | `sbe-workflow`/`tdd-workflow`/`refactor`/`code-review`/`docker-guard` 都是它的阶段 |
| 判据强制 | 每阶段有退出条件，绿灯才前进 |
| 可留证 | 每阶段给可复现命令，避免「看起来完成」 |
| 语言无关 | 方法不绑定 TypeScript。本仓库映射见 §4 |

---

## 4. 流水线在本仓库的落地口径

主 skill 的默认路径与本仓库不同。按下表映射，不改主 skill 的方法。

| 主 skill 默认 | 本仓库实际 | 说明 |
|---|---|---|
| `tests/contract/features/` | `features/` | 已有 6 个 `.feature`，中文 Gherkin |
| `tests/contract/` | `tests/`、`tests/patterns_runtime/` | 验收测试 |
| `tests/contract/glue/` | `tests/_bdd_helper.py`、`tests/step_defs/` | 已有 BDD 胶水 |
| TypeScript / pnpm | Python / pytest | 639 个用例（实测） |
| `pnpm typecheck` | `ruff check .` + `ruff format --check` | 实测通过 |
| — | `tools/standards_check.py` | 17 条判据，实测通过 |
| — | Racket + RackUnit | 编译器侧。**本机 rackunit 缺失** |

**编译器侧硬约束**：本机无 `rackunit`。`compiler/tests/*.rkt` 6 个文件本地不可执行。主 skill 的 TDD 红灯证据只能来自 `pytest` 侧或 CI。

---

## 5. 不能端到端独任的故事

| 故事 | 缺什么 | 只能谁做 |
|---|---|---|
| US-02 | PyPI 版本不可撤回 | 需人工决定开关时机 |
| US-24 | 交付物是文档 | 判据是「文档存在且可读」 |
| US-29 | 真模型 + 真工具 | 需 API key 与环境 |
| US-38 | GitHub Actions 运行 | 需远端 CI |
| US-39 | 追认是决策 | 需人确认基线 |
| US-40/41 | 判据是经验值 | 需实测数值，非通过/失败 |
| US-44 | τ²-bench 真实集不在库内 | 需外部数据 |
| US-51 | 依赖 US-44 | 随 US-44 解锁 |
| US-52 | 人工批准是设计 | 需人批准才合并 |

**这 9 条仍走主 skill。** 只是最后一步需人工或外部输入。

---

## 6. R1 开工顺序建议

依据 `agentlisp-master-plan.md` 的 P0（止血）。P0 三项全绿才进下一阶段。

| 序 | 工作 | 对应故事 | 判据 | 状态 |
|---|---|---|---|---|
| 1 | 修 E2E 红灯 | US-27 第一步 | E2E 用例子进程跑通 | **已完成**（见 `docs/handoff/20261014_p0_1_e2e_red_three_causes_handoff.md`） |
| 2 | 提交门禁 | US-35 | 注入红灯被拒 | **已完成**（见 `docs/handoff/20261014_us35_commit_gate_handoff.md`） |
| 3 | 口径三处对齐 | US-42 | 数字一致 + 脚本核对 | **已完成**（见 `docs/handoff/20261014_us42_pattern_tally_consistency_handoff.md`） |
| 4 | 观察值键文档 | US-24 | 6 个键有用户可见说明 | 待做 |
| 5 | 槽位模型 | US-30 | 槽位数 == 运行时调用点数 | 待做 |
| 6 | 契约栏位机器拦 | US-33 | 栏位缺失 → 判据失败 | 待做 |
| 7 | 21 条 E2E | US-27 | 21 条全绿 | 待做 |
| 8 | v2.3.1 补丁 | US-37 | 制品不含已知不可用项 | 待做 |

**为什么第 1 项最紧**：E2E 红灯在 main 上。它不修，任何「已验证」的说法都不成立。

---

## 7. 未验证

1. **「主 skill 全选 delivery-pipeline」是我的判断。** 依据是「优先端到端」。你若想按阶段分派，本表要改。
2. **§2 的端到端标记是我的判断**，未逐条实跑。
3. **§6 的顺序来自主计划 P0。** 工时未估。
4. **本机 rackunit 缺失**，编译器侧测试的端到端结论本轮不可得。
5. **US-44 真实数据集能否取得，我未试。**
