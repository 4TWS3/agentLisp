# RSI 完全实现：闭环跑通（2026-10-18）

> 判据：规格 §4.2 的 `run_evolution_cycle` 能用真模型、真补丁、真评测跑一轮

---

## 1. 结论

**三条缺口全部补上，闭环真跑通了。** 门禁结果：**rejected**（p=1.0，样本太小）。

过程中 RSI **自己发现并修掉了一个真缺陷**。

---

## 2. 补的三条

| # | 缺口 | 做法 |
|---|---|---|
| 1 | 提案是模板 | `generate_mutation_proposal_with_llm`：把 first_error + 轨迹摘要喂模型，产出 markdown 技能补丁；失败退回模板并在 rationale 记 `fallback=...` |
| 2 | 补丁不进 agent | `agent_eval.run_eval` 把补丁追加到 `system_prompt` 后跑题 |
| 3 | 基准无对比 | `paired_eval`：基线 vs 补丁，同一组题，**精确 McNemar**（二项，n 小也不用卡方近似） |

---

## 3. 实测（DeepSeek v4-flash）

```bash
DEEPSEEK_API_KEY=... python3 -m scripts.evolver.cycle \
  --repo . --agent examples/repair_agent_rsi.al --traces artifacts/online_trace --agent-eval
```

| 项 | 值 |
|---|---|
| 真 trace | `OpenAI HTTP 400: The reasoning_content in the thinking mode must be passed back` |
| 模型生成补丁 | 「thinking 模式下后续请求必须原样回传 `reasoning_content`…」（6 行 markdown） |
| 静态检查 | ran=true, exit=0 |
| new（3 题） | 基线 0.667 → 补丁 **1.0**；b=0, c=1 |
| holdout（3 题） | 补丁 1.0；p=0.25 |
| McNemar p | **1.0**（n=3，无统计力） |
| 门禁 | **rejected** |

**拒绝是对的**：3 对 3 的样本，1 条不一致，不可能显著。

---

## 4. RSI 发现的真缺陷（已修）

补丁内容不是编的：trace 里是 DeepSeek thinking 模式的 400。

**根因**：`base_harness_v2` 追加上一条 assistant 消息时只保留 `content` + `tool_calls`，
把 `reasoning_content` 丢了 → 下一轮 400。

**修法**：assistant 消息原样带上 `reasoning_content`（两条路径：tool_calls 分支与纯文本分支）。
回归测试：`tests/test_tool_message_content_is_str.py::test_reasoning_content_is_passed_back`。

---

## 5. 要让门禁真的通过，还差

| 项 | 说明 |
|---|---|
| 题量 | 现在 6 题（两半各 3）。McNemar 要显著，至少 20-30 题且效果明显 |
| 补丁作用面 | 只改 `system_prompt`；还没到 skills 文件 / 工具参数 |
| 题的性质 | 现在都是「数文件/查版本」这类事实题，模型本来就会；没有真正难的题 |

**定性**：管道 ✓ / 内容真实 ✓ / 统计力 ✗。
