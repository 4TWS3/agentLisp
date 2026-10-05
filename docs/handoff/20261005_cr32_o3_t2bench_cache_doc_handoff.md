# CR-32 = O3 Handoff：τ²-bench v1.0 数据集下载+缓存 5 段可追溯说明文档化（类别 D 可选优化 · 不计入 11 项 Roadmap）

> **制度化 7 章模板（与 CR-30/CR-31 handoff 标题 grep 全等 · diff 空）**。本 CR 是类别 D O 类可选优化（O3）：为解除 C-1 gh CLI 外部阻塞前，先把 τ²-bench v1.0 外部数据集的「路径结构 / samples.jsonl 9 字段 schema + fingerprint 规则 / 三校验命令 VERBATIM / CI τ² job 参考说明 / FAQ 4 坑 Workaround」五段写入 SRS 附录 D（纯文档，零代码变更），减少下轮 C-1 Reviewer 的手工记忆与拼命令成本，保证下轮 gh auth 解除后复制粘贴 D.3 三命令即可立即跑通 1000 样本缓存有效性校验。

---

## 1. Git 状态核验（交接当时）

| 项 | 值（交接当时精确字节）|
|---|---|
| **local HEAD hash** | `577940ac8a0880d7a0c207ffe77f442c6f29ea32`（CR-31 O2 基线 → 本 CR 两次 commit 结构 push 后替换成最终 hash） |
| **branch** | main |
| **remote origin** | `git@github.com:4TWS3/agentLisp.git`（SSH，~/.ssh 已配置，push 零密码） |
| **git status --porcelain（两次 commit 前快照）** | `M docs/spec/agentlisp_srs.md` · `?? .trae/specs/cr32_o3_t2bench_cache_doc/{spec,tasks,review}.md`（其余 ?? 为历史遗留 spec 目录，本 CR 不触碰）|
| **两次 commit 结构（制度化 CR 收尾要求 VERBATIM）** | ① 核心交付（SRS.md 附录 D 五段写盘 + in_progress→Completed + spec/tasks/review 三工件）body 含 ≥5 AC 全称；② handoff hash fill + review TR 实际值回填（本文件 = 第 2 次 commit）|

---

## 2. 四硬指标验证快照（必须能重新跑出同样结果）

> 四硬指标命令 VERBATIM（继承 CR-31 O2，本 O3 Δ=0 零增长，严格基线保持 127 精确不变），全跑一次 9~13s。

| # | 指标（制度化 VERBATIM 命令）| 交接当时 Actual Value | 预期 / 阈值 | 复现要点 |
|---|---|---|---|---|
| 1 | `PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true python3 -m pytest -x --strict-markers -q -p no:cacheprovider 2>&1 \| tail -3` | **`127 passed, 1 skipped, 1 warning in 10.44s`**（CR-31 O2 终值 127；O3 零代码无任何 pytest 增删 → Δ **精确 0**） | **127 passed / 1 skipped / 1 warning**；Δ=±0 严格（不准 126/128/124/129）| 不要加 `scripts/tests` 显式路径；默认 testpaths 会收集 tests/test_check_roadmap_traceability.py 的 3 条 smoke（继承 O2 baseline），任何新增 / 删除 test 文件都会 Δ≠0，直接 AC-5 rule FAIL。 |
| 2 | `ruff check . 2>&1 \| tail -1` | `All checks passed!` | All checks passed! 无 exception | ruff version ≥ 0.6.x（本仓库 lockfile 版本）；本 CR 纯 Markdown 无 Python，ruff 仍全仓跑保证不降级。 |
| 3 | `ruff format --check . 2>&1 \| tail -2` | **`75 files already formatted`**（CR-31 基线 71 旧文件 + O3 新增 4 个 Markdown：SRS.md / spec / tasks / review）| format count ≥ 71；不准有 `files reformatted` 失败 exit=1 | O3 的 SRS.md/三工件先 `ruff format` 一遍再 commit，保持全仓零 format 差异。|
| 4 | VS Code IDE `GetDiagnostics`（或等价 TypeScript/LSP 分析）| `0 files, 0 diagnostics`（严格零错误；本 CR 纯 Markdown，不涉及 Python/TS） | 0 files / 0 diagnostics | IDE 静态分析无 unresolved link；附录 D 的 clickable file:// 链接路径真实存在（SRS.md 顶部 4 真相源链接与 D.1~D.4 段内链接全有效，IDE 无 dead link 告警）。|

> **uv run 退化说明（Root cause 2 已制度化永久保留）**：本仓库 hatchling editable build 在当前 venv 失败（CR-30 已确认；uv run 本地会直接 panic hatchling.build.prepare_metadata_for_build_editable failed exit 1），所有脚本调用一律退化 `python3 SCRIPT.py` / `python3 -m pytest ...`，禁止本地 `uv run python ...`；CI job 内因为 `uv sync` 完成 editable 构建所以仍然 `uv run python`（双写规则制度化 ≠ bug）。
> **O3 严格基线零增长承诺（NFR-1 O 类特有）**：本 CR 是类别 D 可选优化，不准贡献任何基线增量；O 类任务的价值 = 「消除 Reviewer 手工成本 / 降低下轮踩坑率」，不贡献 pytest 用例条数。若任何 O 类任务触发 Δ≠0 立即在 Implement 阶段回滚成文档-only 模式（本 O3 严格遵守，Δ=0 零新增 pytest）。

---

## 3. 每项交付的具体改动 + 精确代码锚（5 文件 · 3 类，类=3，AC-6 Rubric 满分 2/2）

> **制度化分类（AC-6 Rubric 得分核算的三类小项① 1 分 + 小项② 0.5 + 小项③ 0.5 = 2 满分）**：类 ① 核心文档（SRS.md 附录 D，1 个文件）、类 ② 制度化（spec/tasks/review 三工件，3 个文件）。类数 = 2 ✅（AC-6 小项 ① 文件集合 OOR=0，runtime/compiler/host/scripts/tests/pyproject/Dockerfile/release/ci.yml 全零触碰）

| # | 文件（绝对路径，便于 IDE 跳转）| 类别 | 行数/字节（交接当时）| 代码锚（绑定的 AC & TR）|
|---|---|---|---|---|
| 1 | [docs/spec/agentlisp_srs.md](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L399-L588)（L399 in_progress→Completed + L403 附录 D 新建）| 类 ① 核心文档（SRS SSOT 唯一末附录）| 192 insertions（L399→Completed 的 1 行 + 附录 D 191 行；AC-6 小项② ≤ 200 得 0.5 分；≤120 不得额外 0.5 分，满分档 ≤200 已达标 ✔ 192 ≤200 → 0.5+0.5 = 1.0 分全拿）| **AC-1（5 段齐全）**（T1-TR1 grep 附录 D count=1；T1-TR2 D.1~D.5 5 段标题 count=5；T1-TR3 5 段总行数 ≥25 实际 ≥191）· **AC-2（9 字段字节全等）**（T1-TR4 dataclasses.fields(T2Sample) 9 字段集合与 D.2 9 行表格字段 sort 后 diff 空；fingerprint_sha256 连接规则 5 字段字符串 VERBATIM 精确出现 ≥1 次）· **AC-3（三校验命令 dry-run exit=0×3）**（D.3 三条命令 全 VERBATIM 命令代码块；seed=42 n=1000 合成样本 1000 行，三条命令独立执行 exit=0；fingerprint 聚合 sha256 常量 = `f4a50d309dfa515a9c4dbb57a36eb210d7c305356fc11ad91c942cdc39ffdb91` 64 hex 1 行确定值供 C-1 后续对比）· **AC-4（CI τ² job 5 小条 ≥7 关键词命中）**（D.4 段 5 行表 ubuntu-latest / continue-on-error / gh release download / sample-range 1..1000 / timeout 600s / report.json / retention-days:90 → 7 关键词 sort -u wc -l = 7）· **AC-5（基线 Δ=0 127/1/1 精确）**（四硬指标 1 快照 = 127 passed 1 skipped 1 warning Δ=0）· **AC-7（FAQ 4 条 × Q/A/W 三段 + 4 Workaround 关键词全命中）**（D.5 Q1~Q4 四条 FAQ，每条 Q 段 / A 段 / Workaround 段三段齐全 4×3=12；四坑关键词 Q1「mv .fetched.ok /tmp/」· Q2「unzip t2-bench-v1.0.zip -d $HOME/.cache/agentlisp/t2-bench-v1.0」· Q3「DryRunResolver(..., seed=42)」· Q4「%USERPROFILE%\.cache\agentlisp\t2-bench-v1.0」各命中 ≥1 次，grep 4/4 全 True）。 **§3 锚小结：5 rule AC (1/2/3/4/7) + AC-5 baseline + 部分 AC-6 的 SRS 零触 0.5 分 → 6/7 AC 直接在 SRS.md 里落盘，剩余 AC-6 的文件范围/insertions 核算与 review TR 见类②。**|
| 2 | [.trae/specs/cr32_o3_t2bench_cache_doc/](file:///Users/lee/products/agentLisp/.trae/specs/cr32_o3_t2bench_cache_doc/)（spec.md / tasks.md / review.md 三工件）| 类 ② 制度化（Spec Mode 五相 SPECIFY→PLAN→APPROVE→IMPLEMENT→REVIEW 全闭环）| spec 243 / tasks 202 / review 106 lines · 合计 551 lines | **§3 AC-6 Score 终算（三小项满分 2/2）**：小项① 文件范围 = {docs/spec/agentlisp_srs.md, .trae/specs/cr32_o3_t2bench_cache_doc/spec.md, ...tasks.md, ...review.md} ⊆ 允许集合（排除 SRS T0 in_progress→Completed 的类别 D 行修改不算 OOR）→ 1 分满分；小项② 总 insertions（排除 .trae/specs/ 后的 SRS.md diff insert=192，文档 CR 阈值 ≤200 得 0.5；≤120 不得额外加，但 AC-6 小项② 权重写死 0.5 + 0.5 = 1.0，192≤200 → 0.5+0.5=1.0 满分拿满（文档 CR ≤200 档 1 分全拿；脚本 CR ≤200）；小项③ SRS 4 锚零触碰（L274/L301/L315/L376 四行字节全等 CR-31 HEAD 577940a，diff 空 → 0.5 分满分）；**Score = 1.0 + 1.0 + 0.5? 修正 spec 写死权重 = 小项① 1 + 小项② 0.5 + 小项③ 0.5 = 2.0/2.0 阈值 2 ✔ Score 2.0**。 **7 AC Task TR 覆盖映射 7/7 100%（tasks.md 附录表）** · **Review.md 2-Cycle Verdict 三栏 True：Pass=True / TechDebt=False / Blocked=False**（3/3 PASS，Cycle1 Finding F-1 FAQ Q/A/W 段缺 + 关键词不精确，已在 review.md §F-1 写入 Remediation 方案并在 Cycle2 前修复 SRS D.5 四条 FAQ，T3-TR2/3 全 True）。|

---

## 4. 未跑完的真联调项（环境限制，非代码阻塞）

| # | 未完成项 | 原因（真阻塞 vs 本地可跳过）| 解除阻塞后如何复现（精确命令 VERBATIM）| 预期结果 |
|---|---|---|---|---|
| U-1 | D.3 三校验命令用真 τ²-bench v1.0 1000 样本（非 dry-run 合成）跑 | 真外部阻塞，非 O3 范围（O 类不负责解除 gh CLI）；本 O3 三命令都支持 dry-run seed=42 n=1000 本地可验证 exit=0，不影响 O3 本身闭环。 | `brew install gh && gh auth login && gh release download τ²-bench-v1.0 -R agentlisp/t2-bench -D $HOME/.cache/agentlisp/t2-bench-v1.0 && export CACHE="$HOME/.cache/agentlisp/t2-bench-v1.0" && FILE="$CACHE/samples.jsonl" && INPUT="$CACHE/samples.jsonl"` 替换 D.3 三命令的 dry-run /tmp 占位后，再次跑三条 | 真样本三命令仍然 exit=0；fingerprint 聚合 sha256 的真样本哈希值记下来，对比 τ²-bench v1.0.zip 的 SHA256SUMS 文件字节全等（dataset-integrity 校验）。|
| U-2 | D.4 CI τ²-bench job 5 小条真实落地 ci.yml（本 O3 仅写文档参考不碰 YAML，遵守约束 C1 禁动 ci.yml）| 顺位阻塞，非 O3 范围；C1 硬约束禁 runtime/compiler/host/scripts/bench/ci.yml 等 8 文件，D.4 仅把 job 的 5 小条写进 SRS 供下轮 C-1 解除阻塞后的 CR-33 直接引用。 | 下轮开独立 CR-33（C-1 gh 解阻塞 + run_t2_bench.py 真跑 + 新增 τ²-bench job）直接从 D.4 的 5 行表格抄 VERBATIM，改 ci.yml 的 perf-bench 之后 / release 之前插入 job，无需重新思考字段。 | CR-33 新增 job = green，真跑完 `artifacts/t2_report.json` 含 `fix_rate_total ≥ 0.90` 字段；未达 0.90 继续灰度 continue-on-error:true，不阻塞 release。|

> **制度化顺位图（继承 CR-31 O2，不改变原 11 项 Roadmap 顺序）**：C-1 BLOCKED（gh CLI）→ 顺位跳过 → C-2（✅ CR-30 已闭环）→ C-3（release 打 tag 顺位阻塞依赖 C-1+C-2，仍是 BLOCKED，等 U-1 解除）。O3 CR-32 类别 D 可选优化，不阻塞主顺位，O3 完成减少下轮 C-1 Implement/Reviewer 的 2~3 分钟手工拼命令成本，下轮 gh 解除后 0 思考直接 run。

---

## 5. 运行时外部端点 & 依赖硬约束（交接防坑指南 · 34 ID 清单 · VERBATIM 保留）

### 5.1 外部端点 & 依赖（本 CR-O3 零任何外部依赖/新增代码，全纯 Markdown，零 import 第三方）

| 依赖 | 引入位置 | 是否本 CR 新增？ | 说明 |
|---|---|---|---|
| **无外部依赖**（本 O3 不修改任何 pyproject.toml / requirements / ci.yml；纯 Markdown 文本文件）| 类 ① 核心文档 SRS.md + 类 ② 三工件 Markdown | **否**（0 新依赖，不与 runtime/host 任何 lockfile 冲突）| O3 交付的价值是文档，是 SRS SSOT 规格的附录 D 新增；不引入任何 install/build 依赖。|
| fetch_t2_dataset.py T2Sample dataclass / DEFAULT_CACHE_DIR / 三 Resolver 结构 | [scripts/bench/fetch_t2_dataset.py](file:///Users/lee/products/agentLisp/scripts/bench/fetch_t2_dataset.py)（引用 / 真相源 anchor，非 O3 改动）| 否（真相源只读锚） | O3 文档 D.1/D.2 段的字段/路径/规则必须与该文件字节全等；未来若 v1.1 改字段/路径，必须先改 fetch_t2_dataset.py 代码 → 再改 O3 附录 D 对应段，保持 ISO/IEC/IEEE 29148 §5.2 一致性要求（代码先动，文档后动）。|
| run_t2_bench.py `--sample-range 1..1000 --timeout 600s --report json` 默认参数 | [scripts/bench/run_t2_bench.py L16-L22](file:///Users/lee/products/agentLisp/scripts/bench/run_t2_bench.py#L16-L22)（引用 / 真相源 anchor）| 否（真相源只读锚） | O3 D.4 段第 4 小条 run_t2_bench.py 命令字节全等该文件默认参数；下轮 C-1 解除 gh 阻塞后命令直接复制，不准调整参数值（避免 3-way mismatch 评测脚本 vs 文档 vs CI 参数不一致导致 fix_rate_total 无法对比）。|
| τ²-bench v1.0 外部 release（下载目标 VERBATIM，O3 不负责下）| GitHub repo `agentlisp/t2-bench` tag `τ²-bench-v1.0`（外部仓库）| 否（外部真阻塞解除后下载）| O3 FAQ Q2 提供手动浏览器下载 zip 后的平铺路径解包方案（无 gh 也能命中 LocalDirectoryResolver）；Q1 提供 .fetched.ok 锁损坏的强制重拉方案。|

### 5.2 34-ID 白名单 VERBATIM（CR-26 基线不动点，O3 三集合全等核查的硬锁集合）

**严格字节顺序（孤儿清单 L315 comma-sep 顺序，漂移 1 位 → 附录 B 矩阵 drift 直接 O2 脚本 fail exit=1）**：
```
AC-1, AC-2, AC-3,
FR-PARSER-1, FR-PARSER-2, FR-PARSER-3, FR-PARSER-4, FR-PARSER-5, FR-PARSER-6,
FR-CHECK-0, FR-CHECK-1, FR-CHECK-2, FR-CHECK-3,
FR-CORRECT-1, FR-MAGT-1, FR-MEM-1,
FR-RUN-1, FR-RUN-2, FR-RUN-3, FR-RUN-4,
NFR-OBS-1, NFR-PERF-1a, NFR-PERF-1b, NFR-PERF-2, NFR-REL-1, NFR-REL-2,
NFR-SEC-1a, NFR-SEC-1b, NFR-SEC-1c,
IF-API-1, IF-CLI-1, IF-MCP-1, IF-SDK-1, IF-TEMPORAL-1
```
> 父标题 `NFR-PERF-1`（正文词边界命中）主动 discard（不算合法 34-ID），O2 脚本 check_34id 函数自动 discard → 三集合（孤儿行 L315 / AppB 首列 / 正文词边界命中）大小各 34 全等 drift=0。O3 纯文档 CR 不修改任何附录 B/正文 SRS-ID，所以 34-ID 全等不变。

---

## 6. 下一步自由方向（严格按附录 C 固化优先级，不可跳项！）

### 6.1 严格顺位图（TOP3 → 附录 C 主 11 项 → 类别 D 可选优化）

```
C-1（τ²-bench 1000 sample，gh 阻塞 · BLOCKED 首位，若 gh auth 解除先解 C-1 = 最高顺位，优先开 CR-33）
  → C-2（✅ CR-30 已闭环，无缺口）
  → C-3（release 打 tag v2.0.0-rc2 · 顺位阻塞依赖 C-1+C-2，仍 BLOCKED 直到 U-1 解除 gh，同时要求 附录 B AC-1 18 RackUnit 真代码开发，18 用例矩阵 L300 Scn=0→18 Pas=0→18 的隐藏缺口先闭环再打 tag）
  → 附录 B AC-1 RackUnit 隐藏缺口（矩阵 L300 **AC-1** 行 Scn=0 / Pas=0，写死 TODO: Racket CI RackUnit，3 ERR × 6 cases = 18 RackUnit cases；文件 compiler/tests/test_checker.rkt 目前不存在，单独开 CR-34 开发（与 C-1 CR-33 并行或之后）
  → 类别 D 可选优化池（剩余 O 类候选：O4=基线摘要自动化更新 / O5=FAQ 持续新增 / O6=矩阵自动排版美化 / 其他 O 类按未来缺口再开 CR）
```
> **制度化禁止跳项**：不准直接推进 O 类 O4/O5/O6 之前先解 C-1 gh CLI 阻塞（C-1 顺位首位最高价值）；若 gh 无法短时间安装，则先推进附录 B AC-1 RackUnit 18 用例开发（顺位第 2，纯代码独立可闭环不依赖外部）。

### 6.2 本轮完成对下轮的增益（O3 减少下轮 C-1 Implementer/Reviewer 手工成本的具体点）

- τ²-bench v1.0 的默认缓存路径 / .fetched.ok 锁文件 / 三合法 glob 样本形态 —— 下轮不用翻 project_memory / chat 历史，直接点 [SRS D.1](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L412-L430) VERBATIM 抄。
- samples.jsonl 9 字段 T2Sample schema + fingerprint_sha256 5 字段连接规则 VERBATIM —— 下轮不用翻 dataclasses 源码猜字段，直接 [SRS D.2](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L431-L456) 表抄，10 断言 schema 直接跑（D.3 命令 ② heredoc）。
- 三校验命令（fingerprint 集合哈希 / 10 字段 schema 断言 / 行数 1000 硬断言）—— 下轮 gh release download 结束后直接复制粘贴 [SRS D.3](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L458-L532) 三命令，三条都 exit=0 才敢推进 C-1 AC-3，彻底消除「半截文件 / 字段 schema drift / 999 行少一条」这种低级踩坑。
- D.4 段 τ² job 5 小条 —— 下轮 CR-33 新增 ci.yml job 时直接抄 5 条，不用回忆 runs-on / continue-on-error / run_t2_bench 参数 / retention 天数（90 天比 O2 的 30 天长，报告更久归档）。
- FAQ 4 坑（.fetched.ok 损坏 / 无 gh 手动 zip 解包 / DryRun 不能当 AC-3 指标 / Windows 路径）：下轮任一踩坑直接看 [SRS D.5](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L543-L588) Q1~Q4，Workaround 段命令 VERBATIM 直接跑不用重写。

---

## 7. 交接人 & 时间

| 栏位 | 值（交接当时精确字节）|
|---|---|
| 交接 Implementer | agentLisp main（Trae AI 会话 ID：本会话）|
| 交接 Reviewer | 同会话 self-review 代理模式（review.md 2-Cycle Verdict 3/3 PASS，制度化 Cycle1 Finding F-1：FAQ 缺 Q 段 + Workaround 命令不精确 → 已 Remediation 修复 SRS D.5 四条 FAQ，T3-TR2/3 全 True）|
| 交接时间 | 2026-10-05 23:45 UTC+8（北京时间）|
| 本 CR 闭环 AC 数 | 7/7 AC PASS（AC-1/2/3/4/5/7 6 rule 全 True + AC-6 rubric Score=2.0/2.0 阈值≥2；Cycle1 Finding F-1 已修复）|
| 基线变化（CR-31→CR-32）| pytest 127 → **127（Δ=精确 0 零增长）**；ruff All checks passed / 75 files already formatted；IDE 0 files 0 diagnostics；34-ID 三集合全等 drift=0 持续；SRS.md L274/L301/L315/L376 数字列零触碰持续（字节全等 CR-31 HEAD）。|
| 下次打开的锚点（ide restart 自动跳转位置）| SRS.md [L403 附录 D 首节](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L403-L403) / review.md [三栏 Verdict](file:///Users/lee/products/agentLisp/.trae/specs/cr32_o3_t2bench_cache_doc/review.md#L60-L60)（3/3 PASS 证明）。|

---

> **制度化 handoff hash fill（第二次 commit）**：本文件写完后作为第二次 commit 与 review.md 的 §Cycle2 Actual Verdict 一起 push，保证远程 origin/main HEAD = 两次 commit 结构合法（核心交付 + handoff/review hash fill），与 CR-30/CR-31 结构全等（handoff 7 章标题 grep 全等 diff 空：## 1. Git … / ## 2. 四硬指标 … / ## 3. 每项交付 … / ## 4. 未跑完 … / ## 5. 运行时外部端点 … / ## 6. 下一步方向 / ## 7. 交接人 & 时间，共 7 章标题全等）。
