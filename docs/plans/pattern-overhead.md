# 模式接入开销与长跑稳定（US-40 / US-41）

> 来源：非阻塞验收（主计划 §4.1a）。判据是经验值。
> 复现：python3 scripts/bench_pattern_overhead.py

## 1. 读数（2026-10-14，实测）

| 项 | 值 | 阈值 | 判定 |
|---|---|---|---|
| 每轮 handler 平均 | 0.0037 ms | < 1 ms | 通过 |
| p99 | 0.0092 ms | — | — |
| 1000 轮退化比（后 100 / 前 100） | 0.927 | <= 1.2 | 通过 |

环境：macOS · 系统 Python 3.12（Anaconda）· 3 个模式（priority / exception / exploration）。
每轮 = before_turn + on_tool_call + verify_observation 各一遍。

## 2. 说明

- 数字是**经验值**：本机实测，不代表所有环境。
- 只测 pattern 运行时。不含 LLM 与工具 IO。
- 阈值来自主计划 §4.1a（经验值）。
