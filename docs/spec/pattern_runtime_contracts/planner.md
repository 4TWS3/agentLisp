# 契约 CT-PLANNER-01：planner

> 口径来源：compiler/pattern_registry.rkt 的 planner 条目；键取自注册表（合法键，不发明新键）。

| 栏 | 内容 |
|---|---|
| **id** | CT-PLANNER-01 |
| **槽位** | `orchestrate` |
| **输入（合法键）** | :plan-size |
| **期望（可观测）** | pl = h.patterns.api("planner")；assert pl.plan_size() == 3；assert pl.completion(1, 4) == 0.25；且 build_context() 含 [pattern:planner] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、api(kind) 抛 KeyError |
| **端口** | None（纯函数 + 注入，无外部依赖） |
| **不承诺** | 不承诺引擎内部实现；只承诺上述确定性行为 |
