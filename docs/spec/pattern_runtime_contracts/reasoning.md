# 契约 CT-REASONING-01：reasoning（推理技术）

> 口径来源：compiler/pattern_registry.rkt 的 reasoning 条目。

| 栏 | 内容 |
|---|---|
| **id** | CT-REASONING-01 |
| **槽位** | `verify` |
| **输入** | 模式块键：:technique ∈ {cot, tree-of-thought} |
| **期望（可观测）** | technique() 归一化返回；且 build_context() 含 [pattern:reasoning] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、查询口返回空/基线 |
| **端口** | None |
| **不承诺** | 不承诺引擎内部实现细节；只承诺上述确定性、可断言行为 |
