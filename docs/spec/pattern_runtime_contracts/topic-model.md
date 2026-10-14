# 契约 CT-TOPIC_MODEL-01：topic-model

> 口径来源：compiler/pattern_registry.rkt 的 topic-model 条目；键取自注册表。

| 栏 | 内容 |
|---|---|
| **id** | CT-TOPIC_MODEL-01 |
| **槽位** | 无（declaration-only） |
| **输入（合法键）** | :processor |
| **期望（可观测）** | tm = h.patterns.api("topic-model")；assert tm.processor() == "cluster-agent"；assert tm.retrieve("billing") == ["topic: billing"]；assert set(tm.topics(["a", "b"])) == {"T0", "T1"}；且 build_context() 含 [pattern:topic-model] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令 |
| **端口** | Retriever（内存 Mock，构造时告警 adapter=mock ✓ 设计 §7 硬规则） |
| **不承诺** | Mock 适配器仅供测试；生产适配器另排期（批 3 只交付 Mock） |
