# 契约 CT-GOAL_SETTING-01：goal-setting

> 口径来源：compiler/pattern_registry.rkt 的 goal-setting 条目；键取自注册表（合法键，不发明新键）。

| 栏 | 内容 |
|---|---|
| **id** | CT-GOAL_SETTING-01 |
| **输入（合法键）** | :goal |
| **期望（可观测）** | gg = h.patterns.api("goal-setting")；assert gg.goal() == "提高核销率"；assert gg.deviation(0.5) is True and gg.deviation(1.0) is False；且 build_context() 含 [pattern:goal-setting] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、api(kind) 抛 KeyError |
| **端口** | None（纯函数 + 注入，无外部依赖） |
| **不承诺** | 不承诺引擎内部实现；只承诺上述确定性行为 |
