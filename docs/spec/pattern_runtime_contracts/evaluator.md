# 契约 CT-EVALUATOR-01：evaluator（评估器）

> 口径来源：compiler/pattern_registry.rkt 的 evaluator 条目。

| 栏 | 内容 |
|---|---|
| **id** | CT-EVALUATOR-01 |
| **槽位** | `evaluate`、`verify` |
| **输入** | 模式块键：:thresholds 双阈值 |
| **期望（可观测）** | evaluate(0.9/0.5/0.1) → pass/rework/escalate；且 build_context() 含 [pattern:evaluator] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、查询口返回空/基线 |
| **端口** | None |
| **不承诺** | 不承诺引擎内部实现细节；只承诺上述确定性、可断言行为 |
