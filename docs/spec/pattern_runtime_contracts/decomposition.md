# 契约 CT-DECOMPOSITION-01：decomposition

> 口径来源：compiler/pattern_registry.rkt 的 decomposition 条目；键取自注册表（合法键，不发明新键）。

| 栏 | 内容 |
|---|---|
| **id** | CT-DECOMPOSITION-01 |
| **槽位** | 无（declaration-only） |
| **输入（合法键）** | :max-depth |
| **期望（可观测）** | dd = h.patterns.api("decomposition")；assert dd.children("t", 2) == ["t.1", "t.2"]；try:
        dd.children("t", 3)
        raise AssertionError("超过 max-depth 应报错")
    except ValueError:
        pass；且 build_context() 含 [pattern:decomposition] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、api(kind) 抛 KeyError |
| **端口** | None（纯函数 + 注入，无外部依赖） |
| **不承诺** | 不承诺引擎内部实现；只承诺上述确定性行为 |
