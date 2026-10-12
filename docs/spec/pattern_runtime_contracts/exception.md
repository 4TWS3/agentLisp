# 契约 CT-EXCEPTION-01：exception（异常恢复）

> 口径来源：compiler/pattern_registry.rkt 的 exception 条目「异常恢复：retries 与 backoff 声明重试策略」。

| 栏 | 内容 |
|---|---|
| **id** | `CT-EXCEPTION-01` |
| **输入** | .al：`(defexception-agent s :retries 3 :backoff "exponential")`；harness 既有策略 `correct.max_retries = 5` |
| **期望（可观测）** | ① `harness.patterns.retry_policy()` 返回 `{"retries": 3, "backoff": "exponential"}`；② 该策略**不放宽**既有保护：生效值 = `min(pattern.retries, harness.max_retries)` = 3；③ `build_context()` 含 `[pattern:exception]` 指令 |
| **反证** | 去掉 `:pattern`：① `retry_policy()` 返回 `{}`；② `build_context()` 不含 `pattern:exception` |
| **端口** | Clock（退避计时；测试用假时钟，本切片不触发真实等待） |
| **不承诺** | 不承诺改写底层 LLM 客户端的重试实现；只声明策略并与既有 `correct` 策略取更保守者 |
