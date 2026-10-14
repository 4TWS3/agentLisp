# 契约 CT-DECOMPOSER-01：decomposer

> 口径来源：compiler/pattern_registry.rkt 的 decomposer 条目；键取自注册表（合法键，不发明新键）。

| 栏 | 内容 |
|---|---|
| **id** | CT-DECOMPOSER-01 |
| **槽位** | `verify` |
| **输入（合法键）** | :schema-fields |
| **期望（可观测）** | dc = h.patterns.api("decomposer")；ok, bad = dc.validate_payload({"name": "a"})；assert not ok and bad == ["kind"]；且 build_context() 含 [pattern:decomposer] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、api(kind) 抛 KeyError |
| **端口** | None（纯函数 + 注入，无外部依赖） |
| **不承诺** | 不承诺引擎内部实现；只承诺上述确定性行为 |
