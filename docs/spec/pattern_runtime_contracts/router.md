# 契约 CT-ROUTER-01：router

> 口径来源：compiler/pattern_registry.rkt 的 router 条目；键取自注册表（合法键，不发明新键）。

| 栏 | 内容 |
|---|---|
| **id** | CT-ROUTER-01 |
| **输入（合法键）** | :routes（intent=>worker） |
| **期望（可观测）** | rr = h.patterns.api("router")；assert rr.route("deploy") == "ops"；try:
        rr.route("nope")
        raise AssertionError("未覆盖意图应报错")
    except KeyError:
        pass；且 build_context() 含 [pattern:router] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、api(kind) 抛 KeyError |
| **端口** | None（纯函数 + 注入，无外部依赖） |
| **不承诺** | 不承诺引擎内部实现；只承诺上述确定性行为 |
