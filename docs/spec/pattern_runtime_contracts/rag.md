# 契约 CT-RAG-01：rag（检索增强）

> 口径来源：compiler/pattern_registry.rkt 的 rag 条目。

| 栏 | 内容 |
|---|---|
| **id** | CT-RAG-01 |
| **槽位** | `verify` |
| **输入** | 模式块键：无必需键 |
| **期望（可观测）** | verify_evidence(answer, ids) 校验引用；且 build_context() 含 [pattern:rag] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、查询口返回空/基线 |
| **端口** | Retriever（测试用内存 Mock） |
| **不承诺** | 不承诺引擎内部实现细节；只承诺上述确定性、可断言行为 |
