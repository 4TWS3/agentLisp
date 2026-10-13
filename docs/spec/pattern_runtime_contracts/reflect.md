# 契约 CT-REFLECT-01：reflect（反射）

> 口径来源：compiler/pattern_registry.rkt 的 reflect 条目。

| 栏 | 内容 |
|---|---|
| **id** | CT-REFLECT-01 |
| **输入** | 模式块键：:reviewer-agent |
| **期望（可观测）** | reviewer 非空即通过校验；config() 返回 reviewer；且 build_context() 含 [pattern:reflect] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、查询口返回空/基线 |
| **端口** | None |
| **不承诺** | 不承诺引擎内部实现细节；只承诺上述确定性、可断言行为 |
