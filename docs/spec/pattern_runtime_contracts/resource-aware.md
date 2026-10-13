# 契约 CT-RESOURCE_AWARE-01：resource-aware

> 口径来源：compiler/pattern_registry.rkt 的 resource-aware 条目；键取自注册表（合法键，不发明新键）。

| 栏 | 内容 |
|---|---|
| **id** | CT-RESOURCE_AWARE-01 |
| **输入（合法键）** | :budget ∈ {low, mid, high} |
| **期望（可观测）** | ra = h.patterns.api("resource-aware")；assert ra.tier() == "small"；且 build_context() 含 [pattern:resource-aware] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、api(kind) 抛 KeyError |
| **端口** | None（纯函数 + 注入，无外部依赖） |
| **不承诺** | 不承诺引擎内部实现；只承诺上述确定性行为 |
