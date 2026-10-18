# RSI 完全实现评估（2026-10-18）

> 判据：规格 §4.2 的 `run_evolution_cycle` 能跑一轮真循环

---

## 1. 结论

**机制已完整，跑通一轮真循环。** 但"完全实现"还差最后一环：**提案没有真正改变 agent 行为**。

---

## 2. 本轮跑通的真实循环

```bash
python3 -m scripts.evolver.cycle --repo . \
  --agent examples/repair_agent_rsi.al --traces artifacts/online_trace
```

| 步骤 | 实测结果 |
|---|---|
| 读失败轨迹 | 真 trace：`ReAct exceeded max_turns=30`（stage=loop） |
| 生成提案 | `target: prompt-patches` |
| 隔离 worktree | `/tmp/agentLisp-evolver-worktree-patch_...`（创建 + 清理） |
| 静态检查 | **ran=true, exit_code=0**（`static checks PASSED`） |
| 基准（双集） | seed 1 / seed 2，各 n=10：pass_rate 0.9 / 0.9，p=1.0 / 1.0 |
| 门禁 | **rejected**（p=1.0 ≥ 0.05，无显著提升） |

**门禁拒绝是正确的**：没有证据表明补丁更好。

---

## 3. 修的三个问题

| # | 问题 | 修法 |
|---|---|---|
| 1 | worktree 建在仓库父目录，沙箱禁止（git exit 128） | 改到系统临时目录（`AGENTLISP_WORKTREE_ROOT` 可覆盖） |
| 2 | `blocked` 轨迹不算失败证据 | `analyze_failure_traces` 收 `failed` 与 `blocked` |
| 3 | `_default_bench` 用 `--json`（不存在）且双集是同一组数 | 改 `--report json`；两个 seed = 两个不相交样本集 |

---

## 4. 「完全实现」还差什么（关键）

| # | 缺口 | 影响 | 工期（经验值） |
|---|---|---|---|
| 1 | **提案是模板文本**，不是真诊断 | `generate_mutation_proposal` 只把 first_error 拼成一段文字 | 1 天 |
| 2 | **补丁没有进 agent** | 补丁只写进工作区的 `skills/<id>.md`，agent 行为不变 | 1 天 |
| 3 | **基准没有"对比"** | 现在是单边分数，不是「基线 vs 补丁」的差 | 0.5 天 |

三条合起来才是规格里说的「生成补丁 → 隔离验证 → 双集判定」。

**现状定性**：管道 ✓ / 内容 ✗。和之前「模式声明 ✓ / 引擎消费 ✗」是同一类问题。

---

## 5. 未做

- 真模型生成补丁（DeepSeek key 可用，未接）
- 补丁注入（skills / prompt）并在基准里生效
- 基线 vs 补丁的 McNemar 对比
- CI 跑进化循环（只有单测）
