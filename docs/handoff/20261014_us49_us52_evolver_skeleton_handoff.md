# US-49 / US-50 / US-51 / US-52 交底：离线进化链（P7）

> 基线：738 passed · 日期：2026-10-14
> 判据：结构化提案 / Worktree 清理 / 双集 McNemar / 人工批准

---

## 1. 结论

新增 `scripts/evolver/` 四个模块 + 9 条测试。
这是 P7 的**骨架**，不是完整产品：全链路（提案 → worktree → bench → PR）未串。

---

## 2. 四条判据

| 故事 | 判据 | 交付 |
|---|---|---|
| US-49 | 给定失败轨迹产出结构化提案 | `proposal.py`：`generate_mutation_proposal`（带 evidence_trace_id / target / first_error） |
| US-50 | Worktree 验证后清理 | `worktree.py`：`GitWorktree`（正常与异常两路都清理） |
| US-51 | p < 0.05 且通过率达标（双集） | `dual_set.py`：复用 `evolver_gate`（不复制判断） |
| US-52 | 无人工批准不得合并 | `approval.py`：`MergeGate`（空批准人报错） |

---

## 3. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 四条 | pytest scripts/evolver/tests | 9 passed |
| A10 | standards_check | 10 个测试目录被真源覆盖（19/0） |
| ruff | ruff check . | 全过 |

---

## 4. 未做（诚实登记）

- 全链路未串：提案 → worktree 写补丁 → 跑 checker → 跑 bench → 提 PR。
- 提案内容是模板（来自首错信息），不是 LLM 生成。
- US-52 的 PR 自动化（GitHub API）未做。
- 未真跑 bench 双集（需要两套数据集）。
