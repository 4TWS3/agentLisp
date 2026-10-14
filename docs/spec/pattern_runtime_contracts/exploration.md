# 契约 CT-EXPLORATION-01：exploration

> 口径来源：compiler/pattern_registry.rkt 的 exploration 条目；键取自注册表（合法键，不发明新键）。

| 栏 | 内容 |
|---|---|
| **id** | CT-EXPLORATION-01 |
| **槽位** | `budget` |
| **输入（合法键）** | :budget + :convergence |
| **期望（可观测）** | ex = h.patterns.api("exploration")；assert ex.should_stop(3, 0.5) is True；assert ex.should_stop(1, 0.001) is True；assert ex.should_stop(1, 0.5) is False；且 build_context() 含 [pattern:exploration] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、api(kind) 抛 KeyError |
| **端口** | None（纯函数 + 注入，无外部依赖） |
| **不承诺** | 不承诺引擎内部实现；只承诺上述确定性行为 |
