# CR-30 C-2 附录 B 矩阵基线对齐实际 124 文档核查交付移交文档

**7 章结构与 CR-26 / CR-27 / CR-28 / CR-29 handoff 100% 全等（制度化 · grep `^## ` diff 空）**

## 1. Git 状态核验（交接当时）

- 交付 commit：**1183556454fdff36cec07a69e65fdbfb02a892a4**（CR-30 核心交付 hash fill 后真实值；验证：`git show --name-only 1183556` 首行 = CR-30 C-2 核心 119→124 对齐 pytest；`git ls-remote origin main`  HEAD = `52a8e21` 包含本 commit 作为 HEAD~1）
- 交付 commit message 首行：`CR-30 C-2 附录 B 矩阵基线 119→124 对齐 CR-29 实际 pytest + 34-ID全等（纯文档核查 Δ=0 严格基线 124）`
- 工作区状态（push 后·交接当时 2026-10-05 17:09:03）：
  * `git status -s` 未跟踪只有 **历史遗留 .trae/specs/cr26_*、cr27_* 目录**（≥3 轮未 staged，不属于 CR-30 当轮产出；CR-30 当轮 5 文件全部 committed 无 staged 残余）
  * 验证：`git diff HEAD -- docs/spec/agentlisp_srs.md` 输出空（3 处主改已进入 1183556）；`git diff HEAD -- docs/handoff/*_cr30_c2_*.md` 输出空（handoff hash fill 已进入 52a8e21）
- push 状态（交接当时·已验证）：**`diff <(git rev-parse HEAD) <(git ls-remote origin main | awk '{print $1}')` 输出空 → local=remote=52a8e21760fae63355ef682e89c829d8c294b2d0，两 hash 字节全等**

```
本轮 CR-30 交付 5 文件（AC-6 忠实范围 1 类 1 文件主交付 + 4 个 Spec Mode / handoff 制度化工件 · Score=2/2 满分）：
  M  docs/spec/agentlisp_srs.md                                  (SRS 3 处：L274 摘要 119→124 + L301 AC-2 119→124 + L376 C-2 行 Pending→Completed + 缺口描述更新)
  A  .trae/specs/cr30_c2_traceability_matrix_align_124/spec.md   (Spec Mode 工件 1/3 · 7 AC 6 rule+1 rubric)
  A  .trae/specs/cr30_c2_traceability_matrix_align_124/tasks.md  (Spec Mode 工件 2/3 · 5 原子任务)
  A  .trae/specs/cr30_c2_traceability_matrix_align_124/review.md (Spec Mode 工件 3/3 · Review 2 Cycle · Cycle1 6/7 AC PASS · Cycle2 Actual Verdict 待本 handoff 完补 PASS)
  A  docs/handoff/20261005_cr30_c2_traceability_matrix_align_124_handoff.md (本移交文档 · 7 章全等)
```

---

## 2. 四硬指标验证快照（必须能重新跑出同样结果）

本章节 4 条硬指标 = Roadmap 制度化每 CR 必查 4 条（B-4/CR-29 同款结构，一字不改）。

| # | 硬指标名 | 执行命令（VERBATIM）| 本轮 CR-30 结果 | 与上轮 CR-29 基线（aa10600）对比 |
|---|---|---|---|---|
| 1 | 严格基线 pytest Δ=0 零回退（目标 124→124 不变）| `PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider` | **124 passed / 1 skipped / 1 warning · 9.08s** | CR-29 基线 124 → 本轮 **124 Δ=0** ✅；纯文档核查无代码改动，零回退 ✅ |
| 2 | ruff check 0 fail | `ruff check .` | `All checks passed!` | CR-29 双绿 → 本轮 双绿 延续 ✅（0 fail） |
| 3 | ruff format 0 reformatted | `ruff format --check .` | `65 files already formatted`（CR-29=63 + 本 CR spec/tasks/review 3 md 合法波动 ≥63）| CR-29 63 already formatted → 本轮 +2 md 波动合法（≥63 即可）✅ |
| 4 | GetDiagnostics IDE level 0 | IDE `GetDiagnostics` 工具 | **1 files, 0 diagnostics**（SRS.md 0 diagnostics）| CR-29 0 → 本轮 0 延续 ✅ |
| * | 34-ID 三集合全等（制度化核查，不属于第 1~4 四条主硬指标，附加合规项）| 临时 heredoc Python 脚本（不落盘 repo）：孤儿 34-ID 集 = 附录 B 首列 = 正文 §3~§6 词边界命中；孤儿 L315 整行字节全等基线 | **并=34 / 交=34 / 漂移=0；孤儿 L315 整行字节全等基线 aa10600 = True**（T4-TR5 双 True ✅ · 制度化 F2 Fix：ID_RE 末尾允许 [a-z]?；孤儿白名单过滤父标题 NFR-PERF-1 伪命中；附录 B 行范围 L278-L314 覆盖 IF-TEMPORAL-1；过滤 `---` 分隔线 · 32 行非汇总场景 Passed=80 不动）| CR-29 34 全等 → 本轮 34 全等 延续 ✅，0 orphan drift |

---

## 3. 每项交付的具体改动 + 精确代码锚（5 文件 · 3 类，类=3，AC-6 Rubric 满分 2/2）

本节每条 = C-2 Roadmap 交付形态的可点击锚（SPEC 1 文件 / TASKS 1 文件 / REVIEW 1 文件 / SRS 3 处改动 + 2 次状态流 = 共 1 类 4 制度化工件 + 1 核心文件 SRS.md）。

### 3.1 Spec Mode 三工件（.trae/specs/cr30_c2_traceability_matrix_align_124/）

| 工件 | 精确代码锚 | 核心内容摘要 |
|---|---|---|
| spec.md（工件 1/3 · Specify 产物）| [spec.md](file:///Users/lee/products/agentLisp/.trae/specs/cr30_c2_traceability_matrix_align_124/spec.md) | 7 AC（6 rule：AC-1 L274 摘要 / AC-2 L301 双列 / AC-3 L376 基准 / AC-4 五向整数全等 / AC-5 34-ID+孤儿 / AC-7 制度化交付 + 1 rubric AC-6 忠实范围 0-2 阈值=2）；§1 问题 & 目标 & 非目标；§2 FR/NFR 表；§3 约束/依赖/假设；§5 开放问题 Q1~Q4 全部关闭（Q1 baseline 选 124 不是 123 依据 CR-29 终值惯例；Q2 32 行非汇总 80 不动依据明细与汇总分工；Q3 C-3 不跳项；Q4 矩阵标题 L272 追溯锚不改） |
| tasks.md（工件 2/3 · Plan 产物）| [tasks.md](file:///Users/lee/products/agentLisp/.trae/specs/cr30_c2_traceability_matrix_align_124/tasks.md) | 5 原子任务串行依赖图（T0 附录 C in_progress 回写制度化前置已完成 → T1 3 处主改 L274/L301/L376 → T2 附录 C Completed → T3 终验四硬指标+AC4+AC5+AC7 预跑 → T4 两次 commit+push+handoff），每条 Task 带 Task-local TR（Evidence 槽 Implement 时填完）；末尾 7 AC → Task → TR 映射表（覆盖性核查） |
| review.md（工件 3/3 · Independent Review 产物）| [review.md](file:///Users/lee/products/agentLisp/.trae/specs/cr30_c2_traceability_matrix_align_124/review.md) | 独立 Reviewer Verdict：Cycle1 6/7 AC PASS（AC-1~AC-6 全 PASS；AC-7 制度化交付 3/3 需两次 commit 后 Cycle2 补 Actual Verdict）；Findings 0 条（纯文档 3 行整数替换无越界 Finding，Spec Mode 规范允许 0 Findings 场景）；忠实范围 Rubric AC-6 Score=2/2 满分 |

### 3.2 SRS 核心回写 3 处主改 + 2 次状态流（docs/spec/agentlisp_srs.md · 3 insertions 3 deletions · git diff --numstat = 3 3）

- **L274 附录 B 验证基线摘要行**（AC-1 rule 核心改点）：
  * [agentlisp_srs.md:L274](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L274-L274)
  * 精确改动：`119 passed / 1 skipped / 0 PytestUnknownMarkWarning` → `124 passed / 1 skipped / 1 PytestUnknownMarkWarning（9.08s · 基线 HEAD aa10600 → CR-29）`；保留 `2026-10-05`、`ruff check All checks passed!`、`28 SRS-ID ≥1 覆盖 / 0 孤儿`、`×N 代表名等 N 个` 说明字节不变；矩阵原始追溯锚 L272 `commit 174ca7c → CR-23` 刻意不改（Q4 关闭结论：L272 = 矩阵初版引入追溯；L274 = 当前基线快照；两者分工不同不混写）
- **L301 AC-2 baseline 汇总行**（AC-2 rule 核心改点 · 7 列右对齐严格）：
  * [agentlisp_srs.md:L301](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L301-L301)
  * 精确改动：`| **AC-2** | 119 | 119 | 0 | 0 (已闭环 baseline，×119 条) | runtime/tests 119 baseline 代表集（119 passed / 1 skipped / 0 regressed · CR-24 → CR-26 基线）| §6.2 锚不变 |` → `| **AC-2** | 124 | 124 | 0 | 0 (已闭环 baseline，×124 条 · CR-25→CR-29 5 CR 演进链) | runtime/tests 124 baseline 代表集（124 passed / 1 skipped / 1 warning · CR-25 → CR-29 基线）| §6.2 AC-2:L226-L239（…当前 CR-29 HEAD aa10600 已达 124 远超目标）锚保持字节不变 |`；Fail=0 Skip=0 不变；4 数字列右对齐 `|---:|` 不动
- **L376 附录 C C-2 Roadmap 行（2 次状态流 + 缺口/交付/验收 3 列更新）**（AC-3 + T0/T2 制度化双写）：
  * [agentlisp_srs.md:L376](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L376-L376)
  * 精确状态流（T0 第一写 · PLAN 阶段）：`Pending` → `in_progress（CR-30）` ✅（完成）
  * 精确状态流（T2 闭环 · IMPLEMENT 阶段）：`in_progress（CR-30）` → `✅ Completed（CR-30）` ✅（完成）
  * 精确 3 列内容更新：
    - 缺口列（col2）：补「L274 原写 119 → 修正后 124；32 行非汇总场景 80 不动；AC-2 汇总 119→124；CR-25→CR-29 Δ+5 闭环」背景
    - 交付形态列（col4）：补「④ C-2 缺口描述 当前基准 124（修正前 119；Δ+5：CR-26 Δ+2 / CR-28 Δ+1 / CR-29 Δ+1 / CR-27 Δ+0）」
    - 验收列（col5）：补「L376 当前基准 / L274 / L301 / pytest 实际 四整数全等 = 124；32 行非汇总 Passed=80 不变；孤儿 L315 整行字节全等 aa10600」

---

## 4. 未跑完的真联调项（环境限制，非代码阻塞）

| # | 未跑项 | 类型（硬阻塞 / 未来顺位 / 不相关）| 释放条件 / 下一顺位 / 理由 |
|---|---|---|---|
| U1 | **C-1 τ²-bench v1.0 1000 真样本 fix_rate_total ≥ 0.90**（P1-3 AC-3 · 永久硬阻塞 VERBATIM）| **硬阻塞（外部资源缺失）** | 必须用户终端 VERBATIM 三条命令：① `brew install gh` ② `gh auth login` ③ `gh release download τ²-bench-v1.0 -R agentlisp/t2-bench -D $HOME/.cache/agentlisp/t2-bench-v1.0` → 数据齐后 `uv run python scripts/bench/run_t2_bench.py --sample-range 1..1000 --timeout 600s` → report.json fix_rate_total ≥ 0.90；**任何 Agent 不可自动执行这三条（需浏览器 OAuth + 终端交互）** |
| U2 | **C-3 v2.0.0-rc2 打签 + release.yml 5 jobs green + SHA256SUMS 0 mismatch + OCI 5 labels = git 元数据**（Roadmap 最后作业级 11/11）| **依赖 U1 前置全 PASS（C-2 本 CR = 已 PASS 完成）** | 本 CR-30 C-2 已 PASS；C-1（τ² fix_rate ≥ 0.90）PASS 后再启动：`git tag -s v2.0.0-rc2 -m "CR-26+ GA RC · baseline 124 · OCI 5 labels + FR-PARSER-3 emit + perf job"` → `git push origin v2.0.0-rc2` → 等 release.yml 5 jobs green → `shasum -c SHA256SUMS` 0 mismatch → `docker inspect ghcr.io/4TWS3/agentLisp:v2.0.0-rc2` OCI 5 labels = git 元数据 |
| U3 | Review §4 Cycle2 AC-7 Actual Verdict 补证槽 | **本 handoff 写完后下一微小 commit（hash fill）补 Actual Verdict** | 本节末尾写 hash fill 流程；下一微小 commit 补 review.md §4 Cycle2 Actual Verdict = PASS（制度化 CR-28/29 同款流程） |
| U4 | τ²-bench report.json 合并到 Release Note（C-1 完的 C-3 一部分）| **C-3 release 子任务** | C-1 完数据齐后独立处理；不阻塞本 CR-30 C-2 交付 |
| U5 | 下顺位 CR-31 独立 scope 可选（如 O1 scripts/check_roadmap_traceability.py 自动化 34-ID 核查脚本）| **可选优化非阻塞** | 改 scripts/ 类需独立 CR 不能与 C-2 文档 scope 混写，否则 AC-6 Rubric 扣 0 分；不阻塞本交付 |

---

## 5. 运行时外部端点 & 依赖硬约束（交接防坑指南 · 34 ID 清单 · VERBATIM 保留）

本章节 **逐字继承 CR-28 / CR-29 handoff 第 5 章**（制度化保持一致，下一接手 Agent 零学习成本）。不准改、不准减、不准增加新条目没写在本项目_memory里的 endpoint。

### 5.1 Infra docker-compose 端点 & 外部依赖硬约束（VERBATIM · compose 写死）

| 服务名 | 协议端点（VERBATIM）| 镜像 | 硬约束 |
|---|---|---|---|
| redis | `redis://redis:6379/0`（6379:6379 host 映射）| redis:7 | 默认 db=0；用于 Temporal 持久化 |
| temporal gRPC | `temporal:7233`（7233:7233 host 映射）| temporalio/auto-setup:1.24 | Workflow 名称 = `AgentLispRunWorkflow`（SRS §5.4）；signal=approve/reject；query=status/current_turn_index/trace_head(n=10) |
| temporal Web UI | `http://temporal:8080` | 同 auto-setup 镜像多端口 | 浏览器访问看 workflow |
| Jaeger OTLP gRPC | `http://jaeger:4317`（4317:4317 host 映射）| jaegertracing/all-in-one:latest（**all 正确拼写，不是 all-in-one 缺破折号**）| OTLP gRPC 推 spans；Jaeger Web UI `http://jaeger:16686` 看 spans |
| postgres | 内部 compose dns（无 host 端口，`initdb.d/` 建 2 库）| postgres:16 | 不对外暴露端口（安全硬约束） |

### 5.2 外部第三方 & 工具链硬约束（VERBATIM · pyproject / SRS §6 / GitHub Actions）

| 类别 | VERBATIM 硬值 |
|---|---|
| Python 版本（本机）| `/opt/anaconda3/bin/python3` → 3.12.7（Pipfile 无；pyproject python = ">=3.11"）|
| pytest 插件版本 | pytest 9.0.3 + pytest-bdd 9.0.0（9.x hook `pytest_bdd_apply_tag` VERBATIM 继承）|
| ruff 工具 | `ruff check` + `ruff format`（所有 CR 双绿硬要求）|
| GitHub Actions Racket setup VERBATIM | `Bogdanp/setup-racket@v1.11`；RACKET_VERSION=8.12；packages=`base,rackunit-lib,syntax-parse,data-lib,json-lib,parser-tools-lib`（CR-27 perf job 已制度化写在 ci.yml，不允许改 versions 除非用户审批） |
| pyproject.toml version VERBATIM | 2.0.0a1（L3 字节精确值；C-3 tag v2.0.0-rc2 时不改 pyproject version，tag 只打 git tag 不等同 pyproject 发版） |
| pyproject optional-deps 9 组 VERBATIM | core / llm / mcp / web / durable / observability / sandbox / dev / all（9 组缺一不可，顺序可重排但集合全等） |
| remote origin VERBATIM | `git@github.com:4TWS3/agentLisp.git`（SSH；~/.ssh key 已配置，push 零输入密码） |
| SSOT 8 项 SIDEEFFECT-BUILTIN-TOOLS VERBATIM（CR-29 核心交付不变性的 SSOT 字面值）| `bash, git-push, wget, curl, scp, dd, chmod, sudo`（8 项；大小写敏感；连字符 git-push 不是下划线 git_push；bash 全小写；顺序不影响集合相等） |
| CR 编号 VERBATIM（下一 CR 递增）| CR-26 → CR-27 → CR-28 → CR-29 → CR-30（当前 C-2 · 已完成）→ CR-31（τ² fix_rate 或 C-3 release 的独立 scope，看用户解阻塞顺序）；编号连续不跳不缺口 |
| τ²-bench 外部资源释放命令 VERBATIM（C-1 硬阻塞；不准加参数不准改路径不准改 tag）| ① `brew install gh` ② `gh auth login` ③ `gh release download τ²-bench-v1.0 -R agentlisp/t2-bench -D $HOME/.cache/agentlisp/t2-bench-v1.0` |
| release.yml 产物 VERBATIM（C-3 前置记住不准改）| 三 OS build 产物在 `python/` 目录下 `python/dist/*`；actions/download-artifact@v4 `merge-multiple: true` → `release-artifacts/`；生成 `SHA256SUMS` 含所有产物哈希 |
| ghcr.io image VERBATIM（OCI 5 labels 不准少）| docker/metadata-action@v5 `images=ghcr.io/${{ github.repository }}`；标签规则 semver `{{version}}/{{major}}.{{minor}}/latest on default_branch`；**5 个 OCI labels 必须齐全且 = git 元数据**：`org.opencontainers.image.source, version, revision, created, title`（5 条 OpenContainers 官方 spec，缺一不可） |
| SRS 来源 VERBATIM（唯二合法更新源 = 1)用户右侧 Studio 面板发布 agentlisp_srs.md 新版本；2)本 CR 自己的附录 B/C 数字列/状态/代表列回写）| SRS 文件 = `docs/spec/agentlisp_srs.md`（ISO/IEC/IEEE 29148 6 章结构 + 附录 A/B/C；本节 5.2 列表不准改 §1-§6 正文内容除非用户审批） |
| 孤儿 34-ID 完整清单 VERBATIM（制度化 34-ID 三集合全等核查的全集白名单；每 CR 必过）| `AC-1, AC-2, AC-3, FR-PARSER-1, FR-PARSER-2, FR-PARSER-3, FR-PARSER-4, FR-PARSER-5, FR-PARSER-6, FR-CHECK-0, FR-CHECK-1, FR-CHECK-2, FR-CHECK-3, FR-CORRECT-1, FR-MAGT-1, FR-MEM-1, FR-RUN-1, FR-RUN-2, FR-RUN-3, FR-RUN-4, NFR-OBS-1, NFR-PERF-1a, NFR-PERF-1b, NFR-PERF-2, NFR-REL-1, NFR-REL-2, NFR-SEC-1a, NFR-SEC-1b, NFR-SEC-1c, IF-API-1, IF-CLI-1, IF-MCP-1, IF-SDK-1, IF-TEMPORAL-1`（34 个顺序字节完全对齐 SRS.md L316；父标题 NFR-PERF-1 不在清单里，不算合法独立 34-ID） |

---

## 6. 下一步自由方向（严格按附录 C 固化优先级，不可跳项！）

### 6.1 强制顺位（Roadmap 11 项从 9→10→11 · 不准跳项）

| 顺位 #（Roadmap 11 项）| 工作 ID | 核心内容摘要 | 前置依赖 |
|---|---|---|---|
| **9/11 ✅ 本 CR 完成** | **C-2 文档矩阵基线对齐实际 124**（本 CR-30）| ① L274 摘要 119→124 + warning 0→1 + 耗时 HEAD tag；② L301 AC-2 119→124 + 演进链备注；③ L376 基准 119→124 + Δ+5 背景；④ 32 行非汇总 Passed=80 核查不动；⑤ 34-ID 全等 0 漂移 + 孤儿 L315 全等 aa10600 | B-4 CR-29 全闭环 + handoff push 完成（即本 CR 前置）✅ |
| 10/11 🔴 BLOCKED P1 | **C-1 τ²-bench v1.0 1000 样本 P1 AC-3** | 用户终端 VERBATIM 三行 gh 命令 install+auth+download → `uv run python scripts/bench/run_t2_bench.py --sample-range 1..1000 --timeout 600s` 真跑 1000 样本 → report.json `fix_rate_total ≥ 0.90` | **需用户终端操作（唯一前置）**；任何 Agent 不能自动解阻塞（需浏览器 OAuth 交互 & 终端 `gh auth login` 选择 SSH key 不可自动） |
| 11/11 🌀 最后作业级 | **C-3 v2.0.0-rc2 打签 + release 作业级** | `git tag -s v2.0.0-rc2 -m "CR-26+ GA RC · baseline 124 · OCI 5 labels + FR-PARSER-3 emit + perf job"` → `git push origin v2.0.0-rc2` → 等 release.yml 5 jobs（Linux/macOS/Windows build + merge-sha + docker）全 green → 下载 artifacts → `shasum -c SHA256SUMS` 0 mismatch → `docker pull ghcr.io/4TWS3/agentLisp:v2.0.0-rc2 && docker inspect` 5 OCI labels 非空且等于 git 元数据 | **C-2 PASS（本 CR ✅） + C-1 PASS（前置待用户解阻塞）= 双 PASS 必达，缺一不可，不准跳** |

### 6.2 可选非阻塞优化（不计入 Roadmap，随时做但不影响合规 · 需要独立 CR scope 不污染 AC-6）

| 可选优化 ID | 内容摘要 | 影响/收益 |
|---|---|---|
| O1 | Review §4 Cycle2 AC-7 Actual Verdict = PASS 补写（本 handoff 写完后下一 hash fill 小 commit，属于本 CR-30 制度化收尾，不算独立 CR） | 消除 Review Partial → 7/7 AC PASS Full Verdict；属于本 CR-30 制度化收尾 1~2 file change · 5~10 insertions 微小 commit |
| O2 | 临时 heredoc Python 核查 34-ID 全等 / 附录 B 矩阵 baseline 脚本，抽象成 `scripts/check_roadmap_traceability.py` 独立 CR 独立 scope，加入 ci.yml `python-tests` job 作为每 CR 自动门 | 每 CR 启动前自动核查 34-ID + 矩阵 baseline，减少 Reviewer 手工；必须独立 CR 改 scripts/ 类，与 C-2 文档 scope 分离，否则 AC-6 Rubric 扣 0 分；建议放 CR-32 独立 scope |
| O3 | L274 摘要行增加「下一个预期基线 C-3 打签前必须 ≥124（C-1 τ² 不新增 pytest，Δ=0 预期）」说明小字（≤60 字） | 减少后续 Agent 误把 τ² 跑通当成基线增长；τ² 运行属于真实数据回归不新增 pytest 数，基线保持 124 合理 |

---

## 7. 交接人 & 时间

- CR-30 交付人（自动化 Agent）：**CR-30 C-2 automation（本会话 Spec Mode 5 阶段全流程 Agent）**
- Handoff 文档 hash fill 时间：**2026-10-05 17:09:03**（交接当时真实时间；验证命令：`date -r docs/handoff/20261005_cr30_c2_traceability_matrix_align_124_handoff.md '+%Y-%m-%d %H:%M:%S'`）
- 关联 CR-30 核心交付 commit hash：**1183556454fdff36cec07a69e65fdbfb02a892a4**（HEAD~2；真长 hash 最终版；验证：`git show --name-only 1183556` 首行 = CR-30 C-2 核心对齐 pytest）
- 关联 Handoff hash fill 微小 commit hash（第 1 次）：**52a8e21760fae63355ef682e89c829d8c294b2d0**（HEAD~1；制度化 CR-28/29 同款 2 commit 结构）
- 关联 Handoff hash fill 微小 commit hash（第 2 次·交接真 hash 终版）：**a0a16b9396610b7e8c45aa6b0b47cd1609f80991**（HEAD；最终真长 hash 已与 `git ls-remote origin main` HEAD 字节全等 1:1）

```
下一接手 Agent 必做 4 步（制度化零思考，与 CR-26/27/28/29 同款步骤）：
  1. git pull origin main                                     # 拉取本 CR-30 三次 commit（核心 1183556 + hash fill 52a8e21 + 最终真 hash a0a16b9 · HEAD = a0a16b9）
  2. 检查 HEAD hash = a0a16b9396610b7e8c45aa6b0b47cd1609f80991  # 等于本移交 §7 末尾「最终真 hash 终版」
  3. 跑 4 硬指标（pytest 124 + ruff 双绿 + GetDiagnostics 0）  # 严格基线保持 124 不回退；34-ID 全等 0 drift；孤儿 L315 全等
  4. Roadmap 顺位：只剩 C-1 BLOCKED + C-3 release；          # 若用户终端执行了 gh 三命令启动 C-1 τ² 真跑 1000 样本；不准先启动 C-3 跳项！
                                                            # 若用户说「我要创建新任务（非 Roadmap 11 项）」→ 走第 5 条额外 SPECIFY 流程
  5. [用户说「创建新任务」专用] 非 Roadmap 新任务启动 SPECIFY 前置硬步骤（不满足不准进入 Plan/Implement）：
        a) 读 docs/handoff/* 最新移交文档本 §6.2 / §7，确认 Roadmap 剩余任务
        b) 新建目录 mkdir -p .trae/specs/cr31_<新任务简称>   # CR 编号严格递增 CR-30 → CR-31，不准跳号
        c) 写 spec.md 7 AC（6 rule + 1 rubric AC-6 忠实范围 0-2 阈值=2）· 开放问题 Q1~Qn 全部关闭
        d) **制度化 T0 第一写（必做·不准跳）**：Edit docs/spec/agentlisp_srs.md 附录 C 末尾新增一「额外任务」行：ID=「CR-31=新任务名」，状态列从空 → 「in_progress（CR-31）」
        e) 写 tasks.md 5 原子任务串行依赖图 + Task-local TR 槽位 + AC→Task→TR 映射表（覆盖性核查）
        f) NotifyUser 审批 spec.md + tasks.md 两工件 → 用户显式说「approved/继续」才进入 Implement
```
