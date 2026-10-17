# US-43 / US-44 / US-45 交底：首错字段 + 真实数据集 + 评测门槛落点

> 基线：af8d4c5 · 日期：2026-10-14
> 判据（US-43）：ExecutionTraceV2 含首错字段与结构化错误
> 判据（US-44）：run_t2_bench.py --suite t2-bench@v1.0 出非合成 p 值
> 判据（US-45）：scripts/bench/tests/ 存在且含 FR-EVO-4

---

## 1. 结论

三条完成。

---

## 2. US-43（首错）

| 项 | 内容 |
|---|---|
| 新类型 | `StructuredError(code, message, stage, turn_index, hint)` |
| 新字段 | `ExecutionTraceV2.first_error`（只记第一次） |
| 写入点 | blocked / failed / exception 三处 |
| 导出 | `to_dict()` 含 `first_error` |

---

## 3. US-45（评测门槛落点）

| 项 | 内容 |
|---|---|
| 新文件 | `scripts/bench/tests/test_evolver_gate.py`（SRS 指定路径） |
| 新函数 | `run_t2_bench.evolver_gate(pass_rate, p, min_pass_rate=0.90)` |
| 判据 | `pass_rate >= min_pass_rate` 且 `p < 0.05` |

顺带修 A10：`tools/test_paths.txt` 加 `scripts/bench/tests`，A10 从 SKIP 变 PASS。

---

## 4. US-44（真实数据集）

新增 `--suite` 别名（`--dataset` 的别名）。实测用本机缓存数据集：

| 项 | 值 |
|---|---|
| 数据源 | `$HOME/.cache/agentlisp/t2-bench-v1.0`（samples.jsonl） |
| 样本数 | 20（`--sample-range 1..20`） |
| McNemar p | **0.04122683**（非合成；来自真实样本 A/B 配对） |
| fix_rate | 1.0 |
| rubric_mean | 0.90 |
| ac3_pass | true |

---

## 5. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 首错 | pytest tests/test_trace_first_error.py | 2 passed |
| 门槛 | pytest scripts/bench/tests/test_evolver_gate.py | 3 passed |
| 真实集 | run_t2_bench.py --suite … --dataset-dir … | p=0.04122683，ac3_pass=true |
| 判据 | python3 tools/standards_check.py | 19 通过 / 0 失败（A10 不再 skip） |

---

## 6. 未做

- 未跑全量 1000 样本（本轮 20 样本，够证明「非合成」）。
