# 契约 CT-FSM-01：fsm

> 口径来源：compiler/pattern_registry.rkt 的 fsm 条目；键取自注册表（合法键，不发明新键）。

| 栏 | 内容 |
|---|---|
| **id** | CT-FSM-01 |
| **槽位** | `on_tool_call` |
| **输入（合法键）** | :initial-state + :states（from->to:event） |
| **期望（可观测）** | ff = h.patterns.api("fsm")；assert ff.initial_state() == "idle"；assert ff.transition("idle", "start") == "run"；try:
        ff.transition("idle", "finish")
        raise AssertionError("非法迁移应报错")
    except ValueError:
        pass；且 build_context() 含 [pattern:fsm] 指令 |
| **反证** | 去掉 :pattern → handlers 为空、无指令、api(kind) 抛 KeyError |
| **端口** | None（纯函数 + 注入，无外部依赖） |
| **不承诺** | 不承诺引擎内部实现；只承诺上述确定性行为 |
