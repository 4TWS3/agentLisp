# 契约 CT-LEARNING-01：learning

> 口径来源：compiler/pattern_registry.rkt 的 learning 条目；键取自注册表。

| 栏 | 内容 |
|---|---|
| **id** | CT-LEARNING-01 |
| **槽位** | 无（declaration-only） |
| **输入（合法键）** | :skill-dir |
| **期望（可观测）** | ll = h.patterns.api("learning")；assert ll.skill_dir() == ".agentlisp/skills"；k = ll.write_back({"id": "fb1", "text": "慢一步"})；assert "fb1" in k and ll.recall(k) == {"id": "fb1", "text": "慢一步"}；且 build_context() 含 [pattern:learning] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令 |
| **端口** | SkillStore（内存 Mock，构造时告警 adapter=mock ✓ 设计 §7 硬规则） |
| **不承诺** | Mock 适配器仅供测试；生产适配器另排期（批 3 只交付 Mock） |
