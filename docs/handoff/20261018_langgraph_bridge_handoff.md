# :workflow 交给 LangGraph 执行（桥接 + 真实跑通）

> 日期：2026-10-18
> 判据：agentLisp 声明图 → LangGraph 执行 → agentLisp 跑每个节点

---

## 1. 结论

**跑通了。** 用 tianji 的 5 节点同形图（facts → value_judge → operator_eval → improve → report），
DeepSeek v4-flash 真跑，最终产出引用真实数字的研判。

---

## 2. 做了什么

| 项 | 内容 |
|---|---|
| 新模块 | `runtime/langgraph_bridge.py`：把产物里的 `self.WORKFLOW` 变成 LangGraph StateGraph |
| 节点解析 | `handlers[节点名]` → `handlers[:handler 字符串]` → 自动 import `模块.函数` |
| 异步节点 | async def 节点自动 await（agent 节点跑 harness 需要） |
| 条件边 | 同一源的多条 conditional-edge 用 `handlers["<源>__route"]` 路由；缺了报错 |
| 终端节点 | 没有出边的节点自动接 END |
| state | 节点返回 dict 合并进 state（必须带旧 state，否则 LangGraph 整字典替换会丢键） |

**没有改编译器**：`WORKFLOW` 本来就发射了，桥只读它。C1 不受影响。

---

## 3. 实测（examples/tianji_slice）

```bash
DEEPSEEK_API_KEY=... python3 examples/tianji_slice/run_pipeline.py
```

输出：

```
[months] 6
[revenue_trend_pct] 15.0
[net_margin_last_pct] -1.4
[value_judgment] 经营质量判定：表面增长、实质恶化（增收不增利且已由盈转亏）…

=== 最终报告 ===
表面增长、实质恶化。收入120,000→138,000（+15%），净利率20.0%→-1.4%…
建议：7 天定 runway；14 天末月损益四分解；30 天设增量正毛利闸门。
（说明：文中数字全部沿用原三段已给定事实，未新增；runway 待核实。）
```

注意最后那段：模型**自己指出数据矛盾**（burn -18,000 与仅 1 个亏损月冲突），
说明它是基于事实算的，不是编的。

---

## 4. 验证

| 项 | 结果 |
|---|---|
| 桥的单测 | `tests/test_langgraph_bridge.py` 8 passed（线性/异步/缺实现/非 dict/条件边/路由缺/handler 自动导入/output_fields） |
| 真实流水线 | 5 节点全跑，最终报告引用真实数字 |
| 编译器 | 未改（C1 不动） |
| 静态检查 | 编译期就拦住了「output-fields 未在 :state 声明」 |

---

## 5. 分工（定稿）

| 层 | 谁管 |
|---|---|
| 图 / 中断 / 恢复 / checkpoint | **LangGraph**（成熟组件，不自己造） |
| 节点内的 agent（护栏 / 工具 / trace / 模式） | **agentLisp** |

---

## 5.1 state 累积（:reducer，2026-10-18 补）

节点多了一定会遇到「后面节点把前面写的键覆盖掉」。现在 DSL 能声明累积语义：

```lisp
(:state :fields ((chapters :type dict :reducer merge)
                 (trace_log :type list :reducer append :default ())
                 (total :type int :reducer sum :default 0)))
```

| 项 | 说明 |
|---|---|
| 枚举 | `merge`（dict）/ `append`（list）/ `sum`（int/float） |
| 编译期 | 类型不匹配或枚举越界直接报错（`sum` 放到 `str` 上会被拒） |
| 产物 | `STATE_FIELDS[字段]['reducer']` |
| 运行时 | 桥按 reducer 合并；**没声明的字段仍然覆盖**（这是最容易丢数据的地方） |

---

## 5.2 多 agent 编排（subagent 节点，2026-10-18 补）

```lisp
(:workflow :entry a
  :nodes ((a :type subagent :handler "tianji"   :output-fields (judge))
          (b :type subagent :handler "yaoguang" :output-fields (report)))
  :topology ((edge a b)))
```

| 项 | 说明 |
|---|---|
| `:handler` 语义 | subagent 节点是 **agent 注册名**（如 `tianji`），不是模块路径 |
| 编译期 | 按节点类型分别校验：subagent 走 `[A-Za-z_][A-Za-z0-9_-]*`，其它仍要 `模块.函数` |
| 运行时 | `build_graph(..., agents={"tianji": TianjiHarness})`；节点会 new 一个 harness 跑一轮 |
| 输入 | 节点把 state（去掉 messages/chapters）JSON 化作为输入上下文 |
| 输出 | 按 `:output-fields` 落字段 |
| 缺 agent | 报错并列出已注册的名字 |

---

## 5.3 conditional-loop（2026-10-18 补）

```lisp
(:topology ((edge write check)
            (conditional-loop :nodes (write check) :while "need_retry" :max-rounds 3)
            (edge check publish)))
```

| 项 | 说明 |
|---|---|
| 判定函数 | `handlers["<首个节点>__while"]`（或 `handlers[:while 的值]`）；缺了报错点名 |
| 语义 | 跑完 loop 最后一个节点后问判定：真 → 回首个节点；假 → 走原出边（无出边则 END） |
| max_rounds | 到顶直接 done，不看判定；计数由桥给首个节点套的包装器维护 |
| 边冲突 | loop 最后一个节点的**普通出边被接管**，不会同时存在普通边与条件边 |

---

## 6. 未做

| 项 | 说明 |
|---|---|
| interrupt/resume | 桥没包 LangGraph 的 `interrupt`；tianxuan/spec-writer 用了 68 处，需要时在节点里直接用 |
| conditional-loop | 编译器支持，桥只做了 conditional-edge；loop 需要时再加 |
| state reducer | 现在靠节点返回完整 state；`chapters` 那种累加语义要显式写 |
