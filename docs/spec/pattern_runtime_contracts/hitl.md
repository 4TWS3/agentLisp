# 契约 CT-HITL-01：hitl（人在环）

> 口径来源：compiler/pattern_registry.rkt 的 hitl 条目。

| 栏 | 内容 |
|---|---|
| **id** | CT-HITL-01 |
| **槽位** | `on_tool_call` |
| **输入** | 模式块键：:approval-before 阶段 |
| **期望（可观测）** | requires_approval(stage) 判定；且 build_context() 含 [pattern:hitl] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、查询口返回空/基线 |
| **端口** | None |
| **不承诺** | 不承诺引擎内部实现细节；只承诺上述确定性、可断言行为 |
