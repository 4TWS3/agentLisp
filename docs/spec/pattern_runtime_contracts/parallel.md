# 契约 CT-PARALLEL-01：parallel

> 口径来源：compiler/pattern_registry.rkt 的 parallel 条目；键取自注册表（合法键，不发明新键）。

| 栏 | 内容 |
|---|---|
| **id** | CT-PARALLEL-01 |
| **槽位** | `orchestrate` |
| **输入（合法键）** | :branches |
| **期望（可观测）** | pp = h.patterns.api("parallel")；assert pp.fan_in([1, 2]) == [1, 2]；assert pp.branches() == ["a", "b"]；且 build_context() 含 [pattern:parallel] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、api(kind) 抛 KeyError |
| **端口** | None（纯函数 + 注入，无外部依赖） |
| **不承诺** | 不承诺引擎内部实现；只承诺上述确定性行为 |
