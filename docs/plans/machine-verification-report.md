# 机器验证报告

> 范围：agentLisp 仓库（`/Users/lee/products/agentLisp`）
> 基线提交：`9fdd21d`
> 日期：2026-10-14
> 性质：只记**命令输出**。不含推测。
> 未跑项单列一节（第七节）。不跑 = 不知道。

---

## 0. 读数规则

| 标记 | 含义 |
|---|---|
| **实测** | 本轮命令输出。可复现 |
| **未跑** | 本轮未执行。结论不可用 |
| 经验值 | 无外部依据的估计 |

**注意**：本报告不含「通过」的笼统结论。每个数字给命令。

---

## 1. 测试套件

### 1.1 全仓

| 项 | 值 |
|---|---|
| 命令 | `python3 -m pytest -q --no-cov` |
| 采集 | 639 |
| 结果 | **1 failed, 630 passed, 8 skipped** |
| 耗时 | 187 秒 |
| 环境 | 系统 Python 3.12（Anaconda）+ `.racket/bin` 入 PATH |

### 1.2 `tests/` 子集（SRS 复现口径）

| 项 | 值 |
|---|---|
| 命令 | `python3 -m pytest tests/ -q --no-cov` |
| 结果 | **1 failed, 535 passed, 5 skipped** |
| 耗时 | 169 秒 |

**两数不可互推**：选择集不同。

### 1.3 唯一红灯

| 项 | 值 |
|---|---|
| 用例 | `tests/patterns_runtime/test_e2e_compiled_artifact.py::test_e2e_compiled_artifact_loads_patterns` |
| 报错 | `ModuleNotFoundError: No module named 'runtime'` |
| 位置 | 产物第 16 行 `from runtime.base_harness_v2 import …` |

**根因（实测）**：

| 检查 | 结果 |
|---|---|
| 仓库根下 `import runtime` | 成功 |
| 探针脚本在临时目录 + `cwd=仓库根` | `sys.path[0]` = 临时目录 → 失败 |

**判定**：测试环境问题。非产物缺陷。修法见主计划 P0-1。

### 1.4 RackUnit

| 项 | 值 |
|---|---|
| 命令 | `racket -e '(require rackunit)'` |
| 结果 | `collection not found: rackunit` |
| 影响 | `compiler/tests/*.rkt` 6 个文件**本地不可执行** |
| 状态 | **未跑。** 待 CI |

---

## 2. 代码质量判据

| 项 | 命令 | 结果 |
|---|---|---|
| 标准判据 | `python3 tools/standards_check.py` | **17 通过 / 0 失败 / 0 跳过** |
| 静态检查 | `ruff check .` | **All checks passed** |
| 格式 | `ruff format --check tests/ tools/ runtime/ host/` | 全部已格式化 |
| 格式（全仓） | `ruff format --check .` | **1 处失败**：`docs/spec/agentlisp_pattern_runtime_design.md`（既有问题，非本轮引入） |

**判据数变化**：改动前 12 通过 / 4 跳过。跳过原因：检查器找不到 `racket`。本轮修了解析器（PATH 优先，回退 `.racket/bin`）。

---

## 3. 产物漂移闸门

| 步 | 命令 | 退出码 | 输出 |
|---|---|---|---|
| 生成 | `racket compiler/main.rkt -i … -o /tmp/rep.py` | 0 | 无 |
| 只读校验（干净） | 同 + `--check-output-drift` | 0 | `CLEAN` |
| 追加一行后校验 | 同 + `--check-output-drift` | 1 | `DRIFTED` |
| 无 `--force` 重编译 | 同 | **3** | 拒绝写盘 |
| `--force` 重编译 | 同上 + `--force` | 0 | 覆盖成功 |

**四项全部符合设计。实测。**

---

## 4. 契约机械校验（21 份）

| 检查 | 结果 | 判据 |
|---|---|---|
| 六栏齐备 | **21 / 21** | id / 输入 / 期望 / 反证 / 端口 / 不承诺 均非空 |
| 期望实质（> 80 字节） | **15 / 21** | 6 份过短 |
| 期望提到的方法可查 | **21 / 21** | 在 handler / BaseHarnessV2 / PatternRuntime 三者之一 |
| 被测试引用契约 id | **21 / 21** | tests/ 下存在引用该 CT-id 的文件 |
| 契约内登记测试 | **1 / 21** | 只有 `priority.md` 有「落地登记」段 |
| 引擎消费 | **13 / 21** | 见 4.2 |

### 4.1 期望过短的 6 份

| kind | 期望字节 | 引擎消费 |
|---|---|---|
| hitl | 67 | 是 |
| router | 69 | 否 |
| rag | 72 | 是 |
| guardrails-safety | 77 | 是 |
| reflect | 80 | 是 |
| decomposition | 86 | 否 |

**含义**：这些期望只断言「handler 在 + 指令进了上下文」。**未证明行为。**

### 4.2 引擎消费 13 / 21

判据：handler 覆写运行时入口，**或** `PatternRuntime.verify_observation` 有该 kind 的分派。

| 类别 | 数 | 名单 |
|---|---|---|
| 接线消费 | 13 | decomposer、evaluator、exception、exploration、fsm、goal-setting、guardrails-safety、hitl、priority、rag、reasoning、reflect、resource-aware |
| 仅声明 | 8 | a2a、chain、decomposition、learning、parallel、planner、router、topic-model |

**声明与消费脱节：8 处。**

---

## 5. 规格与实现不符（RSI 规格）

| # | 规格写 | 实测 | 命令 |
|---|---|---|---|
| 1 | `:online-trace` / `:offline-evolver` 为合法字段 | 解析器不接受 | 全仓 grep 零命中；`agentlisp_compiler.rkt:205` 只匹配三元组 |
| 2 | 突变目标 4 个（含 `prompt-patches`） | 白名单 **3** 个 | 同文件 `evolution-mutation-targets` |
| 3 | 不变量 4 个（含 `model-provider`） | 白名单 **3** 个 | 同文件 `evolution-invariants` |
| 4 | §3.3 有源码范例 | 文件不存在 | `git ls-files` 无 |
| 5 | 产物字段 `self.evolution_config` | 实际为 `self.EVOLUTION` | grep 产物 |
| 6 | `EVOLUTION` 供运行时读取 | **零引用** | grep 于 `runtime/` `host/` `scripts/` `tools/` 零命中 |

**不符：6 处。**

---

## 6. 声明与消费脱节总账

| 来源 | 项 | 数 |
|---|---|---|
| 模式 | 仅声明 kind | 8 |
| 注册表 | 孤儿条目（`memory`、`multi-agent`） | 2 |
| RSI | `:evolution` 无人读 | 1 |
| RSI | §5 引用的测试文件全缺 | 5 |
| 契约 | 期望未证明行为 | 6 |
| **合计** | | **22** |

**说明**：第 5 行与前 8 处有重叠（6 份过短的期望中，部分属那 8 个仅声明 kind）。**22 是上界，不是并集。**

---

## 7. 未跑项（本轮未执行）

| # | 项 | 为什么未跑 | 影响 |
|---|---|---|---|
| 1 | RackUnit 6 个 `.rkt` 测试 | 本地无 `rackunit` 包 | `compiler/tests/` 全绿不可声明 |
| 2 | 全仓 212 个 skip 的内容 | 缺可选依赖（redis / temporal / e2b 等） | 覆盖率不可声明 |
| 3 | AMS 的 1167 项测试 | 未在本轮范围 | 对 AMS 的判断仍属只读检查 |
| 4 | 真实 τ²-bench（非 dry-run） | 数据集不在库内 | RSI 验收判据不可判 |
| 5 | 真实 LLM 端到端 | 无 API key | 「能跑」只到 mock 层 |
| 6 | Docker 镜像验收 | 未构建 | 分发物自证不可声明 |
| 7 | PyPI 上 `agentlisp` 的现状 | 未联网 | 发布前须核 |
| 8 | `--patterns-report` 全矩阵 | 本轮未触发 | 模式矩阵报告未复核 |

---

## 8. 本轮提交（截至 `9fdd21d` 共 17 个；本报告为第 18 个，不计入）

```
9fdd21d docs(contracts): 清单补入机器检查结果
853c3a5 plan: 记录「发 PyPI」决定并写入硬顺序
9c6a00f docs(contracts): 新增 21 份契约口径确认清单
91581e9 plan: agentLisp 完整开发计划（三线合一）
2b7a3d8 spec(ams): 四项决策已定
a07add8 spec(ams): AMS 特性向 agentLisp 的能力抽取与重构规格
7f2d724 docs(plan): 核对另一会话对本计划的修改
cbd1b42 feat(drift): 产物漂移闸门
2dd6d3b docs(ams): AMS 能力可迁移性实测评估
（其余 8 个为另一会话提交）
```

截至 `9fdd21d`，工作区干净（`git status --short` 无输出）。本报告落盘后即被提交。

---

## 9. 复现命令（逐条）

```bash
cd /Users/lee/products/agentLisp
export PATH="$PWD/.racket/bin:$PATH"

# 1 测试
python3 -m pytest -q --no-cov
python3 -m pytest tests/ -q --no-cov

# 2 判据
python3 tools/standards_check.py
ruff check .
ruff format --check tests/ tools/ runtime/ host/

# 3 漂移闸门
racket compiler/main.rkt -i examples/repair_agent.al -o /tmp/rep.py
racket compiler/main.rkt -i examples/repair_agent.al -o /tmp/rep.py --check-output-drift
printf '\n# hand\n' >> /tmp/rep.py
racket compiler/main.rkt -i examples/repair_agent.al -o /tmp/rep.py --check-output-drift   # 期望 rc=1
racket compiler/main.rkt -i examples/repair_agent.al -o /tmp/rep.py                         # 期望 rc=3

# 4 契约机械校验
python3 - <<'PY'
import csv
p="docs/spec/pattern_runtime_contracts/_口径确认清单.csv"
rows=list(csv.DictReader(open(p,encoding="utf-8-sig")))
print("六栏齐备", sum(r["机器_六栏齐备"]=="是" for r in rows))
print("期望>80B", sum(int(r["机器_期望字节"])>80 for r in rows))
print("被测试引用", sum(int(r["机器_被测试引用"])>0 for r in rows))
print("引擎消费", sum(r["引擎消费"]=="是" for r in rows))
PY
```

---

## 10. 本报告的自限

| # | 限制 |
|---|---|
| 1 | 测试在**系统 Python 3.12** 下跑，非项目 `.venv`（该 `.venv` 为空壳，只有 `_virtualenv.pth`） |
| 2 | 全仓 639 与 `tests/` 541 采集中，skip 的覆盖内容未查 |
| 3 | 「引擎消费」判据只认**显式**覆写或显式 kind 分派。间接消费未计 |
| 4 | 第 6 节的 22 是上界。未去重 |
| 5 | RSI 六处不符基于只读检查，**未运行 AMS 或 RSI 任何代码** |
| 6 | 本报告不含工时。工时在计划文档中，且标为经验值 |
