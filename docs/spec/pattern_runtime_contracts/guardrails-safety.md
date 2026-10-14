# 契约 CT-GUARDRAILS_SAFETY-01：guardrails-safety（护栏安全）

> 口径来源：compiler/pattern_registry.rkt 的 guardrails-safety 条目。

| 栏 | 内容 |
|---|---|
| **id** | CT-GUARDRAILS_SAFETY-01 |
| **槽位** | `verify` |
| **输入** | 模式块键：:hooks 三段 |
| **期望（可观测）** | stages() 返回三段；无 hooks 报错；且 build_context() 含 [pattern:guardrails-safety] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、查询口返回空/基线 |
| **端口** | None |
| **不承诺** | 不承诺引擎内部实现细节；只承诺上述确定性、可断言行为 |
