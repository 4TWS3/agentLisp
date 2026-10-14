# 契约 CT-A2A-01：a2a

> 口径来源：compiler/pattern_registry.rkt 的 a2a 条目；键取自注册表。

| 栏 | 内容 |
|---|---|
| **id** | CT-A2A-01 |
| **槽位** | 无（declaration-only） |
| **输入（合法键）** | :protocol |
| **期望（可观测）** | aa = h.patterns.api("a2a")；assert aa.protocol() == "inmemory"；res = aa.send("worker-1", {"card": "card-7", "id": "m1"})；assert res["delivered"] is True and aa.bus.sent[0]["to"] == "worker-1"；且 build_context() 含 [pattern:a2a] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令 |
| **端口** | MessageBus（内存 Mock，构造时告警 adapter=mock ✓ 设计 §7 硬规则） |
| **不承诺** | Mock 适配器仅供测试；生产适配器另排期（批 3 只交付 Mock） |
