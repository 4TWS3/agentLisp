# RSI 开发计划（前置 + 实现）

> 上位：`docs/plans/agentlisp-master-plan.md` 的 P6 与 P7。
> 规格：[agentlisp-rsi-evolution-tech-spec.md](../spec/agentlisp-rsi-evolution-tech-spec.md)（2.0.0-RSI-DRAFT）。
> 评价：主计划第一部分（六处规格与实现不符、三件前提不满足）。
> 基线：`bd8de4e`

---

## 0. 结论

**RSI 现在不能做。** 三个前提不满足。

| 前提 | 状态 |
|---|---|
| 证据链能定位首错 | 否。`ExecutionTraceV2` 无该字段 |
| 判据可算 | 否。真实 τ²-bench 数据集不在库内 |
| 契约可读 | 否。`EVOLUTION` 全仓零引用 |

本计划先补前提（P6），再实现（P7）。**P6 全绿之前 P7 不启动。**

---

## 1. RSI 要什么

| # | 规格要求 | 位置 |
|---|---|---|
| 1 | `(:evolution ...)` 声明块 | §3.1 |
| 2 | 静态死锁护栏：不可变禁区编译期拒绝 | §1.2 / §4.1 |
| 3 | 在线循环：只读轨迹，禁止自我修改 | §2.1 |
| 4 | 离线循环：定位首错 → 补丁 → 验证 → PR | §2.2 |
| 5 | 双集验证 + McNemar p < 0.05 | §1.2 / §2.2 |
| 6 | Git Worktree 隔离 | §2.2 / §4.2 |

**已有**：#1 与 #2（编译期）。
**缺**：#3 至 #6。

---

## 2. 三件硬前提（P6）

### P6-1 证据链能定位首错

| 项 | 内容 |
|---|---|
| 现状 | `ExecutionTraceV2` 只有 `status` + `error: str` |
| 规格要求 | §2.2 步骤 1「扫描历史轨迹，定位首错位置，输出结构化 JSON 诊断报告」 |
| 缺字段 | 首个失败回合的序号 |
| 缺字段 | 结构化错误：错误类、工具名、入参摘要 |
| 缺字段 | 契约消费点标识（哪个模式在何处介入） |

**验收命令**：

```bash
python3 -m pytest runtime/tests -q --no-cov -k "trace_v2 and first_error"
```

**判据**：存在测试断言 `trace.first_error` 结构含三个字段。

**风险**：加字段可能破坏现有 trace 消费方。**我未查消费方清单。**

### P6-2 判据可算（真实数据集）

| 项 | 内容 |
|---|---|
| 现状 | `scripts/bench/run_t2_bench.py` 只支持 `--dry-run`（合成数据） |
| 规格要求 | §1.2「通过 τ²-bench 端到端回归」；`verifier-gate` 的 `:suite "t2-bench@v1.0"` |
| 问题 | 合成数据上的 McNemar p 值**无统计意义** |

**验收命令**：

```bash
python3 scripts/bench/run_t2_bench.py --suite t2-bench@v1.0 --samples 100
```

**判据**：命令输出含 `pass_rate` 与 `mcnemar_p_value`，且数据非合成。

**这是 RSI 的最大不确定项。** 数据集能否取得，**我未试**。

### P6-3 评测落点

| 项 | 内容 |
|---|---|
| 现状 | `scripts/bench/tests/` 目录**不存在** |
| 规格要求 | FR-EVO-4 = 补丁评估要判 `pass_rate >= min_pass_rate` 且 `mcnemar_p_value < 0.05` |
| 缺 | 该判据无可执行验证 |

**验收命令**：

```bash
python3 -m pytest scripts/bench/tests -q --no-cov
```

**判据**：目录存在，且含 FR-EVO-4 的判据测试。

### P6-4 契约可读

| 项 | 内容 |
|---|---|
| 现状 | 产物含 `self.EVOLUTION`，全仓零引用 |
| 问题 | 契约空转。RSI 的「声明」无人执行 |
| 与主线一致 | 这是「声明与消费脱节」的一个实例（机器验证报告第 6 节） |

**验收命令**：

```bash
grep -rn "EVOLUTION" runtime/ host/ | grep -v __pycache__
```

**判据**：至少一处运行时可观测点读取它，且有测试断言该读取。

---

## 3. 规格修正清单（P7-1）

实测六处不符。逐条给改法。

| # | 规格写 | 实况 | 改法 |
|---|---|---|---|
| 1 | `:online-trace` / `:offline-evolver` 为合法字段 | 解析器只接受固定三元组 | 二选一：删这两个字段，或扩解析器 |
| 2 | 突变目标 4 个（含 `prompt-patches`） | 白名单 3 个 | 决定是否加回 |
| 3 | 不变量 4 个（含 `model-provider`） | 白名单 3 个 | 决定是否加回 |
| 4 | §3.3 有源码范例 `repair_agent_rsi.al` | 不存在 | 删该节，或补范例 |
| 5 | 范例语法是平铺 `(:model :provider ...)` | 现行语法是嵌套 | 范例若补，按现行语法写 |
| 6 | 产物字段 `self.evolution_config` | 实际 `self.EVOLUTION` | 统一为一个名 |

**建议**：

| # | 建议 | 理由 |
|---|---|---|
| 1 | **扩解析器**，加这两个字段 | 在线轨迹开关与离线进化器名都是 RSI 必需 |
| 2 | 加回 `prompt-patches` | 规格 §1.2 把提示词补丁列为进化载体 |
| 3 | 加回 `model-provider` | 换模型是禁区，合理 |
| 4 | 补范例 | 无范例则规格不可执行 |
| 5 | 按现行语法补 | — |
| 6 | 统一为 `EVOLUTION` | 改文档比改代码省 |

---

## 4. 实现项（P7）

| # | 内容 | 依赖 | 验收 |
|---|---|---|---|
| P7-1 | 规格修正（见 §3） | P6 | 五条 FR-EVO 各有测试落点 |
| P7-2 | 在线循环：只读轨迹 | P6-1 | 断言产物未被写 |
| P7-3 | 离线循环：定位首错 → 生成补丁 | P6-1 | 给定失败轨迹，产出结构化提案 |
| P7-4 | Git Worktree 隔离验证 | P6-3 | 验证后 Worktree 被清理 |
| P7-5 | 双集验证 + McNemar | P6-2 | p 值 < 0.05 且通过率达标 |
| P7-6 | 自动提 PR + **人工批准** | P7-5 | 无人工批准不得合并 |

### 4.1 P7-6 的硬约束

规格 §2.2 第 5 步写「合并代码至 `.al` 源码主干」。

**改为**：自动提 PR，**人工批准才合并**。

| 理由 |
|---|
| McNemar p<0.05 只证明统计显著，不证明改动符合意图 |
| 反例：删报告章节可提高通过率，但改坏产品 |

**已记入主计划不变式 I6。**

---

## 5. 五条 FR-EVO 的落点

| 需求 ID | 规格要求 | 落点 | 状态 |
|---|---|---|---|
| FR-EVO-1 | 解析 `(:evolution ...)` | `compiler/tests/test_evolution.rkt` | **文件缺失**。现有 `tests/test_cr42_evolution.py` 覆盖同类 |
| FR-EVO-2 | 越界抛 `ERR_IMMUTABLE_INVARIANT_VIOLATION` | `compiler/tests/test_checker_evolution.rkt` | **文件缺失** |
| FR-EVO-3 | 在线轨迹只读 | `runtime/tests/test_online_trace.py` | **文件缺失** |
| FR-EVO-4 | 补丁评估双阈值 | `scripts/bench/tests/test_evolver_gate.py` | **文件缺失** |
| FR-EVO-5 | Worktree 隔离与清理 | `scripts/evolver/tests/test_git_worktree.py` | **文件缺失** |

**五条全缺。** P7-1 的前置是让五条各有落点。

---

## 6. 门

| 门 | 内容 | 命令 |
|---|---|---|
| G6-a | P6-1 证据链字段 | `pytest runtime/tests -k trace_v2` |
| G6-b | P6-2 真实数据集可跑 | `run_t2_bench.py --suite ...` |
| G6-c | P6-3 评测落点存在 | `pytest scripts/bench/tests` |
| G6-d | P6-4 契约可读 | `grep EVOLUTION runtime/ host/` 非空 |
| G7-a | 五条 FR-EVO 各有测试 | `pytest compiler/tests scripts/` |
| G7-b | 双集 + McNemar 通过 | 见 P7-5 |
| G7-c | 无人工批准不合并 | 见 P7-6 |

**G6 四项全绿 → 才启动 G7。**

---

## 7. 风险

| 项 | 现象 | 根因 | 守 |
|---|---|---|---|
| 数据集取不到 | P6-2 无法通过 | 数据集不在库内 | 若取不到，RSI 判据不可判。**须重估 RSI 是否可做** |
| trace 加字段 | 破坏现有消费方 | 未查消费方清单 | P6-1 先查再改 |
| 自动合并 | 统计显著 ≠ 符合意图 | — | I6：人工批准 |
| 规格与实现漂移 | 六处不符 | 规格先写，实现后走 | P7-1 先修规格 |

---

## 8. 未验证

1. **P6-2 数据集能否取得，我未试。** 这是 RSI 的最大不确定项。
2. **P6-1 加字段是否破坏消费方，我未查清单。**
3. RSI 全部工时**未估**。
4. §3 的六条建议是判断，**未与你确认**。
5. 五条 FR-EVO 的「文件缺失」基于 `git ls-files`，**未核是否有等价覆盖**（FR-EVO-1 疑似有）。
