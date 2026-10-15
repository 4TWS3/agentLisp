# US-14 交底：模式异常不拖垮 Agent（P1-3a）

> 基线：`8a554d3` · 日期：2026-10-14
> 故事：US-14（作为 O，我要模式异常不拖垮 Agent，以便长跑稳定）
> 判据：handler 抛错被捕获 + 留痕 + 测试

---

## 1. 结论

`PatternRuntime` 的 6 个 hook 分发点全部加捕获 + 留痕。handler 抛错不再冒泡。

---

## 2. 两类钩子，两种兜底

| 类 | 钩子 | 抛错后 | 为什么 |
|---|---|---|---|
| 增强 | before_turn / after_turn / order / retry_policy / turn_budget | 跳过该 handler，用原值 | 只是增强，缺了不影响主流程 |
| 安全 | on_tool_call / verify_observation | **按失败拒绝（fail-closed）** | 静默放行 = 护栏失效 |

---

## 3. 留痕

每个抛错记一条事件：`<kind>.<hook>-error`，detail 含 `类型: 消息`。
同时 `logger.exception`。用 `patterns.events_for(kind)` 可查。

---

## 4. 不在捕获范围

`on_init`（加载期配置校验）仍抛出。F-AMS-4：配置错不得静默失活，要早失败。

---

## 5. 实现位置

`runtime/patterns/__init__.py` 的 `PatternRuntime`：

- 新增 `_handler_error(kind, hook, exc)`。
- before_turn / on_tool_call / after_turn / order / retry_policy / turn_budget 各自 try/except。
- verify_observation 拆成外壳 + `_verify_observation_impl`。

---

## 6. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 5 条守卫 | `pytest tests/patterns_runtime/test_exception_isolation.py -q --no-cov` | 5 passed |
| 模式回归 | `pytest tests/patterns_runtime/` | 306 passed |
| 判据 | `python3 tools/standards_check.py` | 18 通过 / 0 失败 |
