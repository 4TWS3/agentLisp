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

## 6. 未做

| 项 | 说明 |
|---|---|
| interrupt/resume | 桥没包 LangGraph 的 `interrupt`；tianxuan/spec-writer 用了 68 处，需要时在节点里直接用 |
| conditional-loop | 编译器支持，桥只做了 conditional-edge；loop 需要时再加 |
| state reducer | 现在靠节点返回完整 state；`chapters` 那种累加语义要显式写 |
