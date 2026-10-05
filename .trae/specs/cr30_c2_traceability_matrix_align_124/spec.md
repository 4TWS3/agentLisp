# CR-30 C-2 附录 B 矩阵基线对齐实际 124 + Passed 列求和核查（Spec Mode 工件 1/3 spec.md）

- 阶段：Specify → Plan → Approve → Implement → Review
- CR 编号：CR-30（Roadmap 11 项第 9/11 顺位 · C 类文档核查首项）
- 唯一 SSOT：`docs/spec/agentlisp_srs.md §附录 B L274 验证基线摘要 + 附录 B L301 AC-2 baseline 行 + 附录 C L376 C-2 缺口描述行`
- 严格基线（CR-29 HEAD aa10600）：`PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider` → `124 passed / 1 skipped / 1 warning（9.08s）`；本轮为纯文档核查，严格基线保持 **124 passed** 不变，Δ=0

---

## 1. 问题 & 目标

### 1.1 问题（SSOT 漂移锚 · 纯数字，无代码改动）
- 附录 B 矩阵「验证基线摘要」L274 明文写 `严格模式 pytest 119 passed / 1 skipped / 0 warning`，但 CR-25→CR-29 已连 5 CR 基线演进：
  - CR-25 cf7ef33：119（Roadmap 起点基线）
  - CR-26 TOP3：119 → 121 / Δ+2（34-ID 三集合全等 + emit 下划线重命名两条顶层函数）
  - CR-27 perf：121 → 122 / Δ+0（perf job 护栏复用 test_harness_v2 内参数化；但 summary 显示 CR-26 Δ+2 120→122，所以 CR-27 实际 Δ+0=122）
  - CR-28 IF-CLI-1：122 → 123 / Δ+1（6 scenario 顶层函数 test_cli_if_cli_1）
  - CR-29 FR-CHECK-2：123 → 124 / Δ+1（SSOT 8 项全等顶层函数 test_sideeffect…8_items）
- 附录 B L301 AC-2 baseline 行 Scenario/Passed 列写 `119 / 119`，未跟随 Δ+5 演进 → 与 pytest 实际报告 124 不一致 5 个计数单位（非漂移，是「文档没回写」）
- 附录 C L376 C-2 缺口描述行正文「当前基准 119」同样未跟实际更新 → 文档 SSOT 3 处数字互相对齐但与代码运行结果矛盾。
- 孤儿清单 L315 34 ID 整行字节全等（制度化 T4-TR5 核查不动）。

### 1.2 目标（本轮交付 · 纯文档 3 处数字改）
只改 `docs/spec/agentlisp_srs.md` 1 个文件 3 处数字（不碰代码 / pytest / ci / release / docker · AC-6 Rubric 类=1 满分 2/2）：
1. **L274 验证基线摘要**：119 → 124，同步更新时间、warning 数（0→1）、耗时（~8s→9.08s）、基线 HEAD（CR-23→CR-29 HEAD aa10600）；
2. **L301 AC-2 baseline 行**：Scenario/Passed 两列 119 → 124；代表列备注改 `×124 条` + CR-25→CR-29 5 CR 演进链说明；锚列保持 §6.2 不变；
3. **L376 C-2 缺口描述**：「当前基准 119」→「当前基准 124（修正前 119；Δ+5 来源：CR-26 Δ+2 / CR-28 Δ+1 / CR-29 Δ+1；CR-27 Δ+0 perf）」。

目标结果：L274 摘要 = L301 AC-2 = L376 C-2 = pytest 实际报告 = **124 passed**，4 处数字 100% 全等（文档 SSOT 一致性闭合）。

### 1.3 非目标（不做 · AC-6 Rubric 越界扣 0 分）
- ❌ 不碰任何 .py / .rkt / .yml / Dockerfile / compose / pytest 代码（纯文档核查）
- ❌ 不改动孤儿清单 L315 34 ID 整行任何字符（制度化要求整行字节全等基线 aa10600 不动）
- ❌ 不改动附录 B 其他 32 条需求行（L278~L299/L302~L311）的 Scenario/Passed 数字（本次已现场核算 32 行 Passed 合计 80，这 32 行是「各 ID 覆盖场景数」不与 AC-2 重复加总，不改）
- ❌ 不改动附录 C 其他行（C-1 τ²-bench BLOCKED 保留；C-3 v2.0.0-rc2 release 作业保留前置依赖 C-2+C-1 双 PASS）
- ❌ 不改动 handoff / review / spec 历史工件（CR-26~CR-29 已归档不动）

---

## 2. 功能 & 非功能需求（FR/NFR · 文档 SSOT 一致性类）

### 2.1 FR（文档一致性，逐条对应 3 处改点）
| FR# | 规格 VERBATIM | 核验方法 |
|---|---|---|
| FR1 | L274 行验证基线：`严格模式 pytest 124 passed / 1 skipped / 1 PytestUnknownMarkWarning（9.08s · 基线 HEAD aa10600 → CR-29）`；28 SRS-ID 覆盖不变，0 孤儿不变 | Read SRS L274 精确字符串包含「124 passed / 1 skipped / 1 warning」；pytest 报告实际 = 124/1/1；三者相等 |
| FR2 | L301 AC-2 baseline 行 7 列：`| **AC-2** | 124 | 124 | 0 | 0 (已闭环 baseline，×124 条 · CR-25→CR-29 5 CR 演进链) | runtime/tests 124 baseline 代表集（124 passed / 1 skipped / 1 warning · CR-25 → CR-29 基线）| §6.2 AC-2:L226-L239 锚保持不变 |` | Read SRS L301 精确 token `124 \| 124`；grep -c 命中 |
| FR3 | L376 C-2 缺口描述：「验证基线 L272：严格模式 pytest 124 passed / 1 skipped；矩阵 L275-L311 Passed 列非汇总 32 行求和 = 80（代表各 ID 覆盖场景；AC-2 汇总行 124 为全集基线不做重复加总）」 | Read SRS L376 精确 token「当前基准 124」；临时 heredoc Python 求和 32 行 Passed = 80（不变） |
| FR4 | 文档 SSOT 四向全等：L274 summary pass_count = L301 AC-2 Scenario = L301 AC-2 Passed = L376 C-2 基准 = pytest 实际 passed = **124** | 临时 heredoc 统一读 4 源取 int → 断言全等 len(set({124,124,124,124,124})) = 1 |
| FR5 | 孤儿清单 L315 整行字节全等基线 aa10600（制度化 34-ID 三集合全等） | `git show HEAD:docs/spec/agentlisp_srs.md | sed -n '315p'` 结果 = 当前文件 L315 整行 diff 空；三集合（orphan=34 / appb=34 / body=34）并=34 交=34 漂移=0 |

### 2.2 NFR（非功能 · 纯文档合规类）
| NFR# | 内容 |
|---|---|
| NFR1 | 严格基线 pytest 保持 **124 passed / 1 skipped / 1 warning**，Δ=0（纯文档不允许任何代码改动影响基线）；ruff / GetDiagnostics 0 |
| NFR2 | AC-6 Rubric 忠实范围 0-2 阈值=2：**修改类=1（只 docs/spec 1 类，不碰 runtime/tests / .trae/specs 历史 / compiler / ci / release / docker）· 修改文件=1（agentlisp_srs.md 单一文件）· 行数≤6（只改 3 行 1-2 词替换）** |
| NFR3 | git diff HEAD --stat 只有 `docs/spec/agentlisp_srs.md` 1 个文件，insertions ≤ 10 / deletions ≤ 10（轻量文档核查不做大段改动） |
| NFR4 | 附录 B 7 列列头 `| 需求 ID | Scenario 数 | Passed | Failed | Skip/Xfail | pytest / RackUnit 代表性用例 ID | 代码锚 |` 字节全等不动；4 数字列右对齐 `|---:|` 不动 |
| NFR5 | 制度化两次 commit 结构（核心 + handoff hash fill）延续 CR-26/28/29；两次 commit message 全用 `commit -F /tmp/*.txt` 长文无 zsh 分词风险 |
| NFR6 | handoff 7 章标题与 CR-26/27/28/29 四份 `grep "^## "` diff 空（制度化零学习成本交接） |

---

## 3. 约束 / 依赖 / 假设

| 类型 | 条目（VERBATIM） |
|---|---|
| **约束** | ① 只改 docs/spec 1 类；② 不改孤儿 L315；③ 不触发 pytest 基线 Δ≠0；④ C-2 完成后 C-3 release 必须等 C-1 τ²-bench 用户解阻塞 |
| **依赖** | CR-29 B-4 已 7/7 AC PASS（124 Δ+1 已稳定，不回滚）；HEAD aa10600 = origin/main 对齐 |
| **假设** | 本轮真跑 pytest 124 仍然稳定（不出现 flaky；若 flaky，先在 chat 上报 flaky case + 触发项，不把 flaky 当成文档错修）|

---

## 4. Acceptance Criteria（6 rule + 1 rubric = 7 AC）

### AC-1：L274 摘要四字段精确替换（rule）
- **Given** HEAD aa10600 SRS L274 现写 `119 passed / 1 skipped / 0 warning`
- **When** 编辑 SRS L274 仅替换数字/时间/HEAD 标签
- **Then** 行内 token：`124 passed` / `1 skipped` / `1 warning` / `HEAD aa10600 → CR-29` 全部精准存在；时间日期 = 2026-10-05
- **Pass Condition** `grep -n "严格模式 pytest 124 passed / 1 skipped / 1" docs/spec/agentlisp_srs.md` 命中 1 行（L274）
- **Evidence** Read SRS L274 + pytest 实际报告尾行截图

### AC-2：L301 AC-2 行 119→124 双列替换 + 备注更新（rule）
- **Given** L301 现写 `\| **AC-2** \| 119 \| 119 \| 0 \| 0 (已闭环 baseline，×119 条)`
- **When** 编辑 Scenario/Passed 两列 int 119→124 + 代表列备注 `×124 条 · CR-25→CR-29 5 CR 演进链`
- **Then** `awk -F\| '$2~"AC-2"{gsub(/ /,"",$3);gsub(/ /,"",$4);print $3,$4}'` = `124 124`；7 列列数不变；代表列双反引号（若有）保持对齐 FR-CHECK-2 格式
- **Pass Condition** 临时 heredoc awk 输出精确 `124 124`
- **Evidence** Read SRS L301 屏幕截图行

### AC-3：L376 C-2 缺口描述基准 119→124（rule）
- **Given** L376 现写「验证基线 L272：严格模式 pytest 119 passed / 1 skipped」
- **When** 把 `119 passed` → `124 passed`；补一句不超 40 字说明：`（修正前 119；Δ+5：CR-26 Δ+2 / CR-28 Δ+1 / CR-29 Δ+1 / CR-27 Δ+0）`
- **Then** `sed -n '376p' docs/spec/agentlisp_srs.md` token `当前基准 124` 精确命中；行数不变；不碰阻塞条件/释放命令/C-1/C-3 其他两行列
- **Pass Condition** `grep -c "当前基准 124" docs/spec/agentlisp_srs.md` = 1
- **Evidence** Read SRS L376 屏幕截图行

### AC-4：文档 SSOT 五向整数全等（rule）
- **Given** SRS 4 位置 + pytest 实际共 5 个 int 来源
- **When** 临时 heredoc Python：① re 读 L274 first int passed；② awk 读 L301 col3 col4；③ re 读 L376 first int passed；④ subprocess 跑 pytest 取尾行 passed 数
- **Then** len(set({v1, v2, v3, v4, v5})) == 1 且值 == 124
- **Pass Condition** heredoc exit code = 0 且 stdout 包含 `★ SSOT 全等 = 124`
- **Evidence** heredoc 全量 stdout（不落盘 repo）

### AC-5：孤儿清单 L315 整行字节全等基线 aa10600 + 34-ID 三集合全等漂移 0（rule）
- **Given** 制度化核查项（每 CR 必跑，不允许 silent 漂移孤儿）
- **When** `diff <(git show HEAD:docs/spec/agentlisp_srs.md | sed -n '315p') <(sed -n '315p' docs/spec/agentlisp_srs.md)` + 临时 heredoc Python T4-TR5 三集合：orphan_set / appb_set / body_set
- **Then** diff 空输出；三并 = 34；三交 = 34；漂移 = 0
- **Pass Condition** diff exit 0；heredoc 输出 `并=34 交=34 漂移=0`
- **Evidence** diff stdout 空 + heredoc stdout

### AC-6：忠实范围 Rubric（rubric）
- **Dimension** 改动类与文件范围的克制度（类=1 满分；类≥3 越界 0 分）
- **Scale** 0-2
- **Anchors**：0 = 改了 runtime/tests / compiler / ci / release / docker 任一类 或 ≥6 文件；1 = 改 docs + specs 2 类 或 2-3 文件 ≤20 行；2 = **严格 1 类只 docs/spec，1 文件，≤6 行改动 insertions+deletions ≤20**
- **Pass Threshold** ≥ 2（满分要求 · 纯文档核查 CR-30 必须严格克制）
- **Evidence** `git diff HEAD --name-only | wc -l` = 1；`git diff HEAD --stat` 文件名 = `docs/spec/agentlisp_srs.md`；`git diff HEAD --numstat` ins+del ≤ 20

### AC-7：制度化交付 3/3 全 PASS（rule · 与 CR-29 AC-7 同类）
- **Given** CR-26~CR-29 均已满足：① 两次 commit 结构（核心 + handoff hash fill）；② handoff 7 章标题四份全等；③ `commit -F` 长文
- **When** CR-30 交付时执行同样结构
- **Then** ① commit graph 显示 2 commits 连续；② `diff <(grep "^## " docs/handoff/20261005_cr29_b4_fr_check2_ssot_8_handoff.md) <(grep "^## " docs/handoff/*_cr30_c2_*_handoff.md)` 输出空；③ `git log --oneline -n 2 | xargs -I{} git show -s --format=%B {} | head -n 30 | grep -c "^-"` ≥ 10（长文 -F 无单行 -m）
- **Pass Condition** 3 条 3/3 全 TRUE
- **Evidence** git log 链 + diff 空输出 + commit message 预览

---

## 5. Open Questions（启动前已全部关闭 · 无遗留）

| Q# | 问题 | 关闭结论（SPECIFY 阶段现场核查明） |
|---|---|---|
| Q1 | AC-2 baseline 写 123 还是 124？CR-27/28 AC-2 写的是「最终 CR 基线」惯例 | **Q1 结论：写 124**（CR-28 AC-2 行写 123 = 当时最终 CR-28 基线 123；CR-29 已 Δ+1，所以 CR-30 写 CR-29 终值 124，延续「AC-2 = 最新 CR HEAD 基线」惯例） |
| Q2 | 32 行非汇总行 Passed 合计 80 要改到 124 - 44 吗？ | **Q2 结论：32 行不动**（32 行 = 各 ID 覆盖场景明细；AC-2 行 = 全集基线包含参数化重复项；两者不是加总关系，80+重复项=124，符合 CR-26 同样结构（CR-26 32 行明细 + AC-2 119 基线） |
| Q3 | C-3 release 前置依赖 C-2+C-1，C-2 完了能直接启动 C-3 吗？ | **Q3 结论：不能**（C-1 τ²-bench 永久阻塞 VERBATIM 需用户执行 gh 安装+auth+release download，C-2 完只能把 Roadmap 进度推进到「9/11 完成；C-1 BLOCKED 待解；C-3 等 C-1」，不允许跳） |
| Q4 | 矩阵标题 L272 写「commit 174ca7c → CR-23」要改 HEAD aa10600 吗？ | **Q4 结论：不改**（L272 标题是「矩阵初版引入 commit 174ca7c 追溯锚」，写死不动；基线当前值在下方 L274 摘要行体现，两者分工不同；改 L272 会破坏矩阵初版引入追溯链） |
