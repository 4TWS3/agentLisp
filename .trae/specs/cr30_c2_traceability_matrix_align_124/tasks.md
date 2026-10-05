# CR-30 C-2 附录 B 矩阵基线对齐实际 124（Spec Mode 工件 2/3 tasks.md）

- 关联 spec.md：`.trae/specs/cr30_c2_traceability_matrix_align_124/spec.md`（7 AC：AC-1~AC-7 = 6 rule + 1 rubric）
- 严格基线 CR-29 HEAD aa10600：124 passed / 1 skipped / 1 warning · 9.08s（纯文档核查 Δ=0）

---

## Task 0：制度化 T0 回写附录 C Roadmap C-2 Pending → in_progress（CR-30）
- **Status**: pending → in_progress（Plan 阶段立刻执行，不允许跳）
- **Priority**: high
- **Depends On**: spec.md 审批前（T0 是整个 CR 的前置写）
- **Description**：
  - Edit SRS 附录 C L376 行「验收 PASS 判据」列或最后一列状态字段，从 `Pending` → `in_progress（CR-30）`（不阻塞 C-1/C-3；不改其他 4 列字节）
  - 与 CR-26~CR-29 T0 第一写完全同流程；T0 完才允许写 tasks.md 其他任务 Status 改 pending
- **Task-local Test Requirements**：
  - **TR-0.1（rule）**：`grep -n "in_progress（CR-30）" docs/spec/agentlisp_srs.md` 命中 L376；C-1/C-3 行无 `in_progress` 污染
  - **TR-0.2（rule）**：`git diff HEAD -- docs/spec/agentlisp_srs.md | diffstat -D` 只改 1 行；L376 外无字节改动（除 T0 外暂不允许 T1~T3 提前改）
- **Blocking**: 本任务完 → 进入 Task 1（3 处数字主改）

---

## Task 1：Edit SRS 3 处 119 → 124 整数全等（L274/L301/L376）
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 0
- **Description**：
  1. **L274 摘要行**（2~3 词替换 + 时间/HEAD tag）：旧 `严格模式 pytest 119 passed / 1 skipped / 0 PytestUnknownMarkWarning；… commit 174ca7c → CR-23` → 新 `严格模式 pytest 124 passed / 1 skipped / 1 PytestUnknownMarkWarning（9.08s · 基线 HEAD aa10600 → CR-29）；28 SRS-ID 均有 ≥1 条测试覆盖，0 条孤儿需求`（保留 28/0 孤儿不变；保留 commit 174ca7c → CR-23 原始矩阵锚不动，新增「基线 HEAD aa10600 → CR-29」小字标签）
  2. **L301 AC-2 行**（Scenario/Passed 双列 119→124 + 代表列备注）：旧 `\| **AC-2** \| 119 \| 119 \| 0 \| 0 (已闭环 baseline，×119 条) \| runtime/tests 119 baseline 代表集（119 passed / 1 skipped / 0 regressed · CR-24 → CR-26 基线）` → 新 `\| **AC-2** \| 124 \| 124 \| 0 \| 0 (已闭环 baseline，×124 条 · CR-25→CR-29 5 CR 演进链) \| runtime/tests 124 baseline 代表集（124 passed / 1 skipped / 1 warning · CR-25 → CR-29 基线）`；锚列 §6.2 不变
  3. **L376 C-2 行**（缺口描述列「当前基准 119」→ 124 + Δ+5 说明 ≤40 字）：在缺口描述末尾加小字 `（修正前 119；Δ+5：CR-26 Δ+2 / CR-28 Δ+1 / CR-29 Δ+1 / CR-27 Δ+0）`
- **Task-local Test Requirements**：
  - **TR-1.1（rule）**：`sed -n '274p' docs/spec/agentlisp_srs.md | grep -c "124 passed / 1 skipped / 1"` = 1；时间日期 `2026-10-05` 精确存在
  - **TR-1.2（rule）**：`awk -F\| '$2~/\*\*AC-2\*\*/{gsub(/ /,"",$3);gsub(/ /,"",$4);print $3"|"$4}' docs/spec/agentlisp_srs.md` 精确输出 `124|124`；其余 col5=0 col6=0
  - **TR-1.3（rule）**：`sed -n '376p' docs/spec/agentlisp_srs.md | grep -c "当前基准 124"` = 1；Δ+5 说明 4 项 CR-编号齐全：CR-26 / CR-28 / CR-29 / CR-27
  - **TR-1.4（rubric · AC-6 映射）**：忠实范围 0-2，≥2 才 PASS：
    - Evidence ① 改类=1（只有 docs/spec）② 改文件=1 ③ `git diff HEAD --numstat docs/spec/agentlisp_srs.md` ins+del ≤ 20
    - Score 2：全部满足；Score 1：2/3；Score 0：≤1/3
- **Blocking**: Task 1 TR 全 PASS → Task 2 状态回写
- **Completion Evidence（预填槽位）**：3 个 Edit 工具调用 ID + 3 条 TR PASS 证据行号

---

## Task 2：回写附录 C Roadmap C-2 状态 → ✅ Completed（CR-30）
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 1（所有 TR PASS 才允许把 in_progress 改 Completed；不允许跳过 Task 1 先改状态）
- **Description**：
  - Edit SRS L376 末尾状态列从 `in_progress（CR-30）` → `✅ Completed（CR-30）`
  - 其余 4 列（缺口 / 阻塞原因 / 交付形态 / 验收判据）字节完全不动（制度化：状态改只改最后一列）
- **Task-local Test Requirements**：
  - **TR-2.1（rule）**：`grep -n "✅ Completed（CR-30）" docs/spec/agentlisp_srs.md` 命中且只命中 L376；C-1 仍然 BLOCKED 不动；C-3 仍然 Pending 不动
  - **TR-2.2（rule）**：`git diff HEAD -- docs/spec/agentlisp_srs.md | wc -l` ≤ 120（3 处主改 + 2 次状态流 = 最多 5 行级改动；≥150 说明有越界）
- **Completion Evidence（预填槽位）**：Edit 工具调用 ID + grep 证据

---

## Task 3：制度化 5 章终验（四硬指标 + 34-ID全等 + 孤儿 L315 全等 + AC 自检）
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 2
- **Description**：
  1. **TR-3.1 四硬指标快照**：严格 pytest 124 Δ=0；ruff check 双绿；ruff format 0 reformat；GetDiagnostics 0
  2. **TR-3.2 34-ID 三集合全等（制度化核查）**：孤儿 L315 拆 ID 34 个（用 `replace("，", ",") + split(",")`，不用 regex split 有歧义）；附录 B L278-L311 首列去 `---` 分隔线去 `**`；正文 §3~§6 词边界命中 ID_RE `\b(AC-[123]|FR-[A-Z]+-\d|NFR-[A-Z]+-\d[a-z]?|IF-[A-Z]+-\d)\b` 末尾允许 `[a-z]?`
  3. **TR-3.3 孤儿 L315 整行字节全等基线 HEAD aa10600**：`diff <(git show HEAD:docs/spec/agentlisp_srs.md | sed -n '315p') <(sed -n '315p' docs/spec/agentlisp_srs.md)` 输出空
  4. **TR-3.4 AC-4 文档 SSOT 五向整数全等 124**：临时 heredoc Python 读 L274 / L301 col3 / L301 col4 / L376 / pytest 实际 → set size = 1
  5. **TR-3.5 AC-7 制度化交付 3 项自检预跑（不等 commit）**：① 规划 2 次 commit；② handoff 7 章标题对齐 CR-29；③ commit message 写 -F 长文文件
- **Task-local Test Requirements**：上面 5 条 TR-3.1~TR-3.5 全部 pass；一条 fail 本任务保持 in_progress，绝不允许进入 Task 4
- **Completion Evidence（预填槽位）**：pytest 尾行 + ruff stdout + GetDiagnostics + heredoc 34-ID stdout + diff 空 + heredoc AC-4 stdout

---

## Task 4：制度化两次 commit + push + handoff 7 章全等 CR-29 模板
- **Status**: pending
- **Priority**: high
- **Depends On**: Task 3
- **Description**：
  1. **Commit 1（核心交付）**：只 add `docs/spec/agentlisp_srs.md`（3 处主改 + T0/T2 两次状态流 = 同一文件 1 个 commit）；message 写 `/tmp/cr30_commit_msg.txt` 长文（标题：`CR-30 C-2 附录 B 矩阵基线 119→124 对齐 CR-29 实际 pytest + 34-ID全等（纯文档 3 处 Δ=0）`；Body：列出 3 处改点 L274/L301/L376 + AC-1~AC-7 逐条 verdict ；7 AC 用 `- [x] AC-1` 格式）
  2. **Handoff 写 + Review Cycle2 补 Actual Verdict**：
     - Write `docs/handoff/20261005_cr30_c2_traceability_matrix_align_124_handoff.md` 7 章；章标题严格用 CR-29 handoff `grep "^## "` 输出逐字 copy（标题里的 CR-29 → CR-30、B-4 → C-2 等标签说明允许替换）
     - Write `.trae/specs/cr30_c2_traceability_matrix_align_124/review.md` §4 Cycle2 Actual Verdict = AC-7 PASS（制度化 Review 2 Cycle）
  3. **Commit 2（handoff hash fill + review cycle2 actual verdict）**：add handoff + review.md 两文件；message 写 `/tmp/cr30_handoff_hashfill_msg.txt` 长文
  4. **Push**：`git push origin main`；验证 `git rev-parse HEAD == git ls-remote origin main | awk '{print $1}'` 全等
- **Task-local Test Requirements**：
  - **TR-4.1（rule）**：`git push origin main` 成功无冲突；local=remote HEAD hash
  - **TR-4.2（rule）**：`diff <(grep "^## " docs/handoff/20261005_cr29_b4_fr_check2_ssot_8_handoff.md) <(grep "^## " docs/handoff/20261005_cr30_c2_traceability_matrix_align_124_handoff.md)` 输出空（7 章标题字节全等 count=7/7）
  - **TR-4.3（rule）**：两次 commit message 来源 `cat /tmp/cr30_*.txt` 与 `git log -n 2 --format=%B` diff 空；单行 `-m` 真调用 0 次（制度化 `grep -c "git commit -m"` 命令历史 = 0）
- **Completion Evidence（预填槽位）**：push 成功 stdout；diff 空 stdout；2 commits hash list

---

## 总 AC → Task → TR 映射表（覆盖性核查 7 AC 全有 TR 证据）

| Acceptance Criterion | 类型 | 对应 Task + TR | 证据采集时点 |
|---|---|---|---|
| AC-1 L274 摘要替换 | rule | Task 1 · TR-1.1 | Implement Task 1 |
| AC-2 L301 AC-2 双列 | rule | Task 1 · TR-1.2 | Implement Task 1 |
| AC-3 L376 C-2 基准 | rule | Task 1 · TR-1.3 | Implement Task 1 |
| AC-4 SSOT 五向全等 | rule | Task 3 · TR-3.4 | Implement Task 3 |
| AC-5 34-ID全等+孤儿 L315 | rule | Task 3 · TR-3.2 + TR-3.3 | Implement Task 3 |
| **AC-6 忠实范围 Rubric** | **rubric · 0-2 阈值=2** | Task 1 · TR-1.4 | Implement Task 1（`git diff --numstat` 实采） |
| AC-7 制度化交付 3/3 | rule | Task 4 · TR-4.1/4.2/4.3 | Implement Task 4（push 后实采） |
