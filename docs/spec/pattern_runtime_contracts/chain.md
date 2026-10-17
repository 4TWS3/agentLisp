# 契约 CT-CHAIN-01：chain

> 口径来源：compiler/pattern_registry.rkt 的 chain 条目；键取自注册表（合法键，不发明新键）。

| 栏 | 内容 |
|---|---|
| **id** | CT-CHAIN-01 |
| **槽位** | `orchestrate` |
| **输入（合法键）** | :steps |
| **期望（可观测）** | cc = h.patterns.api("chain")；assert cc.steps() == ["plan", "act"]；assert cc.next_step(1) == "act" and cc.next_step(2) is None；且 build_context() 含 [pattern:chain] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、api(kind) 抛 KeyError |
| **端口** | None（纯函数 + 注入，无外部依赖） |
| **不承诺** | 不承诺引擎内部实现；只承诺上述确定性行为 |
