# AgentLisp v2.0 递归自我进化 (RSI) 规格说明书

文档代号：agentlisp_tech_spec_rsi
版本：2.0.0-RSI-DRAFT
基线日期：2026-10-07
适用对象：AgentLisp 核心编译器与运行时开发团队
标准规范：ISO/IEC/IEEE 29148:2018 需求工程标准

---

> ## ⚠️ 实况口径（as-built，2026-10-14 实测，基线提交 a54ce5f）
>
> 本文是**设计草案**（2.0.0-RSI-DRAFT）。实现情况经机械核对如下：
>
> | 本文要求 | 实况 | 证据 |
> |---|---|---|
> | §3.1 EBNF 扩展（:evolution 块） | **已实现，仅编译期** ✓ | compiler/agentlisp_compiler.rkt:181 / 196 / 198（解析 + 越界拦截 + emit） |
> | §3.2 突变目标与不可变禁区 | **已实现，仅编译期校验** ✓ | 同上：越界的 :evolution 在编译期被拦下 |
> | §3.3 源码范例 repair_agent_rsi.al | **不存在** ✗ | git ls-files 无此文件 |
> | §4.1 Racket 前端改造 | **部分**：:evolution 已支持；离线驱动未做 | 运行时/宿主引用 EVOLUTION = **0 处** |
> | §4.2 离线流水线脚本 | **未实现** ✗ | scripts/ 与 tools/ 无 rsi / evolution 脚本 |
> | §2 双循环（在线 + 离线进化） | **离线进化循环未实现** ✗ | 全仓 RSI 相关文件仅本规格 1 份 |
> | §5 可追溯矩阵 / §6 验收清单 | 待与实现同步 | 本文档内 |
>
> **结论**：RSI 现状 = **编译期契约可用 ✓ / 运行时与离线闭环未实现 ✗**。
> 与设计模式那条链同形：声明 ✓ / 执行 ✗。投产 RSI 需按 §4.2 新建离线流水线（工作量未估）。
>
> 防误读：**不要把本规格当作已实现能力的清单**。判据以运行时代码与测试为准。
## 1. 导言与设计动机

### 1.1 背景与核心痛点

AgentLisp v2.0 包含四层编译架构。
架构内置四重安全护栏。
传统 Agent 系统遇到边缘失败，依赖人工分析轨迹。
工程师人工修正提示词和工具。
人工试错响应滞后，成本高昂。
这种方式缺少统计学验证。
修正局部缺陷容易导致全局能力退化。

根据《深入理解 AI Agent》，进化载体分为三层：

| 进化层级 | 载体类型 | 作用特点 |
| :--- | :--- | :--- |
| **层级 1** | 任务内上下文适应 | 包含单次任务内的 ReAct 轮次与短记忆，不跨任务保留。 |
| **层级 2** | 外部制品更新 | 包含 Skill、Prompt 与 Harness 规约，可持久化与审计。 |
| **层级 3** | 模型参数更新 | 包含 SFT、强化学习与偏好对齐，更新开销高。 |

AgentLisp 递归自我进化（RSI）聚焦第 2 层。
第 2 层指外部制品更新。
系统将自举修改表达为 S-表达式与 Skill 补丁。
此机制提升系统自举进化能力。

### 1.2 目标与核心原则

本规范指导团队在现有代码库上落地双循环 RSI 机制。
系统实现三个核心目标：

1. **声明式进化契约**
   在 DSL 增加 `(:evolution ...)` 声明原语。
   原语划分子区。
   区分可进化突变区与不可变安全禁区。

2. **静态死锁护栏**
   静态编译器在编译期对不可变禁区执行死锁断言。
   编译器拒绝修改沙箱路径的重写。
   编译器拒绝越权命令清单的重写。

3. **统计显著性双集验证**
   生成的代码通过隔离 Git Worktree 验证。
   生成提示词补丁通过隔离 Git Worktree 验证。
   补丁通过 $\tau^2$-bench 端到端回归测试。
   补丁通过 McNemar 配对卡方显著性检验（$p < 0.05$）。

---

## 2. 双循环 RSI 总体架构设计

双循环 RSI 架构区分“在线执行”与“离线进化”。

| 循环类型 | 核心职责 | 访问权限 |
| :--- | :--- | :--- |
| **在线执行循环** | 处理真实业务，生成只读轨迹日志。 | 只读访问 `.al` 编译产物，无修改权限。 |
| **离线进化循环** | 分析失败轨迹，生成并验证补丁。 | 隔离 Git Worktree 读写，通过检验后提交 PR。 |

### 2.1 在线执行循环 (Online Loop)

1. **记录不可变证据链**
   在线 Harness 按照追加模式运行。
   系统记录 Thought、Action 与 Observation。
   记录内容写入 `ExecutionTraceV2`。
   错误码写入 OTel Span 树。

2. **隔离运行**
   在线执行引擎取消自我修改权限。
   引擎只读取编译确认的 `.al` 产物。

### 2.2 离线进化循环 (Offline Loop)

离线自举流水线由 Meta-Diagnosis Agent 驱动。
执行步骤如下：

1. **定位首错**
   扫描历史轨迹。
   定位首错位置。
   输出结构化 JSON 诊断报告。

2. **生成最小补丁**
   遵循 Context Engineering 原则。
   拒绝全局重写系统提示词。
   生成带有唯一 ID 的增量补丁。

3. **签订变更契约**
   契约包含失败证据与根因推断。
   契约包含修改提案与预期行为。

4. **双集验证**
   在边界集上验证修复效果。
   在保留集上验证防止退化。
   要求 McNemar 检验满足 $p < 0.05$。

5. **自动合并**
   在 Git Worktree 沙箱中运行验证。
   验证通过后提交 Pull Request。
   合并代码至 `.al` 源码主干。

---

## 3. AgentLisp 语言规范扩展

DSL 语法树扩展 **`(:evolution ...)`** 配置块。

### 3.1 EBNF 语法树扩展

```ebnf
(* AgentLisp v2.0 顶层声明扩展 *)
AgentDecl         ::= "(" "defagent" AgentName StaticBlock DynamicBlock HarnessBlock [EvolutionBlock] [MultiAgentBlock] ")"

(* RSI 自自我进化配置块 *)
EvolutionBlock    ::= "(" ":evolution" EvolutionProperty+ ")"
EvolutionProperty ::= ":online-trace" Boolean
                    | ":offline-evolver" String
                    | ":mutation-targets" "(" TargetSymbol+ ")"
                    | ":immutable-invariants" "(" InvariantSymbol+ ")"
                    | ":verifier-gate" VerifierGateSpec

TargetSymbol      ::= 'skills | 'prompt-patches | 'harness-retry | 'pattern-macros
InvariantSymbol   ::= 'kv-alignment | 'workspace-root | 'forbidden-commands | 'model-provider
VerifierGateSpec  ::= "(" ":suite" String ":min-pass-rate" Float ":mcnemar-p-threshold" Float ")"
```

### 3.2 突变目标与不可变禁区

| 规约属性 | 允许枚举值 | 约束说明 |
| :--- | :--- | :--- |
| **`:mutation-targets`** | `'skills`, `'prompt-patches`, `'harness-retry`, `'pattern-macros` | 授权离线进化器改写的目标。 |
| **`:immutable-invariants`** | `'kv-alignment`, `'workspace-root`, `'forbidden-commands`, `'model-provider` | 绝对禁止离线进化器改写的禁区。 |

注意：侵入禁区触发编译错误。

### 3.3 源码范例 (`repair_agent_rsi.al`)

```lisp
(defagent production-repair-agent-rsi
  ;; 1. 静态前缀块 (Static Block)
  (:model
    :provider "anthropic"
    :name "claude-3-7-sonnet"
    :temperature 0.2
    :system-prompt "你是一个严谨的代码修复 Agent。操作原则：读取记忆 -> 隔离修改 -> 运行 Pytest 校验。")

  (:tools
    (import-builtin read-file edit-file bash)
    (import-mcp "stdio://python ./mcp_servers/github_mcp.py"))

  ;; 2. 动态上下文块 (Dynamic Block)
  (:context
    :memory (:markdown-fs "./workspace" :layers (L0-Abstract L1-Overview L2-FullText) :auto-append #t)
    :skills (python-debugging git-workflow)
    :status-bar (:step-count #t :time-tracker #t :todo-list #t))

  ;; 3. Harness 三重工程护栏块
  (:harness
    (constrain
      :forbidden-commands ("rm -rf /" "git reset --hard" "drop database")
      :require-human-approval (git-push deploy-production)
      :workspace-root "./workspace")
    (verify
      :json-schema #t
      :linter-check #t
      :test-runner "pytest tests/")
    (correct
      :max-retries 3
      :circuit-breaker 5
      :on-failure ask-human))

  ;; 4. 原生 RSI 递归自我进化块 (Evolution Block)
  (:evolution
    :online-trace #t
    :offline-evolver "meta-diagnosis-agent"
    :mutation-targets (skills prompt-patches harness-retry pattern-macros)
    :immutable-invariants (kv-alignment workspace-root forbidden-commands)
    :verifier-gate (:suite "t2-bench@v1.0" :min-pass-rate 0.90 :mcnemar-p-threshold 0.05)))
```

---

## 4. 编译器与转译器改造指南

### 4.1 Racket 编译前端改造

1. **解析 AST 节点**
   匹配 `(:evolution ...)` 配置块。
   提取结构化 AST。

2. **检查静态禁区**
   新增静态检查断言 `FR-CHECK-EVO-1`。
   突变目标侵入不可变禁区时，终止编译。
   输出 `ERR_IMMUTABLE_INVARIANT_VIOLATION`。

3. **生成 Python 配置**
   转译节点为 `self.evolution_config` 字典。
   运行时读取字典。

### 4.2 离线流水线脚本

实现流程如下：

```python
import os
import subprocess
import json
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class MutationProposal:
    proposal_id: str
    target: str
    diff_content: str
    evidence_trace_id: str


class OfflineEvolver:
    def __init__(self, agent_src_path: str, bench_suite: str):
        self.agent_src_path = agent_src_path
        self.bench_suite = bench_suite

    def analyze_failure_traces(self, trace_dir: str) -> List[Dict[str, Any]]:
        """1. 定位首错位置"""
        failures = []
        for file in os.listdir(trace_dir):
            if file.endswith(".json"):
                with open(os.path.join(trace_dir, file)) as f:
                    trace = json.load(f)
                    if trace.get("status") == "failed":
                        failures.append(trace)
        return failures

    def generate_mutation_proposal(self, failure_trace: Dict) -> MutationProposal:
        """2. 生成最小补丁"""
        return MutationProposal(
            proposal_id="patch_001",
            target="skills",
            diff_content="## Python Debugging Rule\n- 遇到 KeyError 时，先输出 dict.keys()",
            evidence_trace_id=failure_trace["run_id"],
        )

    def evaluate_in_worktree(self, proposal: MutationProposal) -> bool:
        """3. 在隔离 Git Worktree 运行验证"""
        worktree_dir = f"/tmp/worktree_{proposal.proposal_id}"
        subprocess.run(["git", "worktree", "add", worktree_dir, "HEAD"], check=True)
        try:
            patch_file = os.path.join(worktree_dir, "skills", f"{proposal.proposal_id}.md")
            os.makedirs(os.path.dirname(patch_file), exist_ok=True)
            with open(patch_file, "w") as f:
                f.write(proposal.diff_content)

            res = subprocess.run(
                ["racket", "compiler/main.rkt", "--check-only", "-i", self.agent_src_path],
                cwd=worktree_dir,
            )
            if res.returncode != 0:
                print("静态断言失败：突变目标侵入不可变禁区")
                return False

            bench_res = subprocess.run(
                ["python", "scripts/bench/run_t2_bench.py", "--suite", self.bench_suite],
                cwd=worktree_dir,
                capture_output=True,
                text=True,
            )
            bench_data = json.loads(bench_res.stdout)

            if bench_data["pass_rate"] >= 0.90 and bench_data["mcnemar_p_value"] < 0.05:
                return True
            return False
        finally:
            subprocess.run(["git", "worktree", "remove", "-f", worktree_dir], check=True)

    def run_evolution_cycle(self, trace_dir: str):
        failures = self.analyze_failure_traces(trace_dir)
        for failure in failures:
            proposal = self.generate_mutation_proposal(failure)
            passed = self.evaluate_in_worktree(proposal)
            if passed:
                print(f"提案 {proposal.proposal_id} 验证通过，合并代码至主干")
                break
```

---

## 5. 需求与测试可追溯性矩阵

| 需求 ID | 验证条件 (ISO 29148) | 测试用例 |
| :--- | :--- | :--- |
| **FR-EVO-1** | `parse-defagent` 解析 `(:evolution ...)` 块并返回结构化 AST。 | `compiler/tests/test_evolution.rkt` |
| **FR-EVO-2** | 突变目标侵入 `:immutable-invariants` 时，抛出 `ERR_IMMUTABLE_INVARIANT_VIOLATION` 并退出。 | `compiler/tests/test_checker_evolution.rkt` |
| **FR-EVO-3** | `:online-trace #t` 开启时，完整写入元数据，禁止写回 `.al` 源码。 | `runtime/tests/test_online_trace.py` |
| **FR-EVO-4** | 补丁评估要求 `pass_rate >= min_pass_rate` 且 `mcnemar_p_value < 0.05`。 | `scripts/bench/tests/test_evolver_gate.py` |
| **FR-EVO-5** | 评估过程在独立临时 Git Worktree 运行，结束后清理 Worktree。 | `scripts/evolver/tests/test_git_worktree.py` |

---

## 6. 交付与验收清单

合并 RSI 模块至主干分支前，完成以下核验：

- [ ] 更新 EBNF 语法扩展块。
- [ ] 扩展 Racket 编译前端。
- [ ] 落地离线自举脚本。
- [ ] 补充 BDD 测试契约。
- [ ] 配置 CI 流水线。
