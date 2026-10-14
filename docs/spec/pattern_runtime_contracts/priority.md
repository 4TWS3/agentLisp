# 契约 CT-PRIORITY-01：priority（优先级排序）

> 口径来源：compiler/pattern_registry.rkt 的 priority 条目「优先级排序：按 criteria 排序，levels 指定层数」。
> 本契约先冻结，再写实现（设计 v2 §5）。

| 栏 | 内容 |
|---|---|
| **id** | `CT-PRIORITY-01` |
| **槽位** | `order` |
| **输入** | .al：`(defpriority-agent s :criteria "urgency" :levels 3)`；运行时：候选列表 `[{"id": "a", "urgency": 1}, {"id": "b", "urgency": 3}, {"id": "c", "urgency": 2}]` |
| **期望（可观测）** | ① `harness.patterns.order(candidates)` 返回按 `urgency` **降序**：b, c, a；② `harness.build_context()` 中多出一条 system 消息，文本含 `pattern:priority` 与 `criteria=urgency`、`levels=3` |
| **反证** | 去掉 `:pattern`（普通 `(define-agent …)`）：① `order()` 返回**原顺序** a, b, c；② `build_context()` **不含** `pattern:priority` |
| **端口** | None（纯函数 + 上下文注入，无外部依赖） |
| **不承诺** | 不承诺模型内部打分；不承诺对不含 `criteria` 字段的元素做重排（保持稳定） |

## 落地登记

| 项 | 值 |
|---|---|
| 运行时 handler | `runtime/patterns/priority.py` |
| 测试 | `tests/patterns_runtime/test_priority.py`（行为 1 条 + 反证 1 条） |
| 状态 | 见 `runtime/patterns/__init__.py` 的 `LANDED` |
