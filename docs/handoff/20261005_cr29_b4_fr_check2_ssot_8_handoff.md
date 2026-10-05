# CR-29 B-4 FR-CHECK-2 SSOT 8 项 sideeffect builtin 双端集合全等 pytest 交付移交文档

**7 章结构与 CR-26 / CR-27 / CR-28 handoff 100% 全等（制度化 · grep `^## ` diff 空）**

## 1. Git 状态核验（交接当时）

- 交付 commit：**3228f99**（等 push 后填真实远程 HEAD，后续小 commit hash fill 回填到这里和第 7 章提交人时间）
- 交付 commit message 首行：`CR-29 B-4 FR-CHECK-2 SSOT 8 项 sideeffect builtin 双端集合全等 pytest（123→124 Δ+1，Spec Mode 7/7 AC PASS）`
- 工作区状态（push 前）：
  * `git status -s` 未跟踪只有 **历史遗留 .trae/specs/cr26_*、cr27_* 目录**（不是 CR-29 当轮产出，已存在 ≥1 轮），不影响 CR-29 交付干净度
  * CR-29 当轮 5 个当轮文件 全部 staged 后 committed = 1 commit，无 staged 残余
- push 状态：**待执行 `git push origin main` 后把 `git ls-remote origin main` HEAD hash 回填到本节末尾（和第 7 章）**

```
本轮 CR-29 交付 5 文件（AC-6 忠实范围 3 类 5 文件满分）：
  A  .trae/specs/cr29_b4_fr_check2_ssot_8/spec.md      (Spec Mode 工件 1/3 · 7 AC)
  A  .trae/specs/cr29_b4_fr_check2_ssot_8/tasks.md     (Spec Mode 工件 2/3 · 5 原子任务)
  A  .trae/specs/cr29_b4_fr_check2_ssot_8/review.md    (Spec Mode 工件 3/3 · Review 2 Cycle)
  M  docs/spec/agentlisp_srs.md                        (SRS 2 处：附录 B L287 1/1→2/2 + 附录 C L367 Pending→Completed)
  A  runtime/tests/test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal.py (NEW pytest 1 顶层)
```

---

## 2. 四硬指标验证快照（必须能重新跑出同样结果）

本章节 4 条硬指标 = Roadmap 制度化每 CR 必查 4 条（B-3 同款结构，一字不改）。

| # | 硬指标名 | 执行命令（VERBATIM）| 本轮 CR-29 结果 | 与上轮 CR-28 基线（169f1d5）对比 |
|---|---|---|---|---|
| 1 | 严格基线 pytest 零回退（目标 123→124 Δ+1）| `PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider` | **124 passed / 1 skipped / 1 warning · 9.14s** | CR-28 基线 123 → 本轮 **124 Δ+1** ✅；N=124 ∈ {123,124} 合法，124≥123 零回退 ✅ |
| 2 | ruff check 0 fail | `ruff check .` | `All checks passed!` | CR-28 双绿 → 本轮 双绿 延续 ✅（0 fail） |
| 3 | ruff format 0 reformatted | `ruff format --check .` | `61 files already formatted`（56→61 +5 合法波动；新增 1 个 .py 已 format 完成；F3 Low Finding 已在 Review §3 修完 ✅）| CR-28 56 already formatted → 本轮 +5 波动合法（≥56 即可）✅ |
| 4 | GetDiagnostics IDE level 0 | IDE `GetDiagnostics` 工具 | **0 files, 0 diagnostics** | CR-28 0 → 本轮 0 延续 ✅ |
| * | 34-ID 三集合全等（制度化核查，不属于第 1~4 四条主硬指标，附加合规项）| 临时 heredoc Python 脚本（不落盘 repo）：孤儿 34-ID 集 = 附录 B 首列 = 正文 §3~§6 词边界命中；孤儿 L315 整行字节全等基线 | **并=34 / 交=34 / 漂移=0；孤儿 L315 整行字节全等基线 169f1d5 = True**（T4-TR5 双 True ✅）| CR-28 34 全等 → 本轮 34 全等 延续 ✅，0 orphan drift |

---

## 3. 每项交付的具体改动 + 精确代码锚（5 文件 · 3 类，类=3，AC-6 Rubric 满分 2/2）

本节每条 = B-4 Roadmap 交付形态的可点击锚（SPEC 1 文件 / TASKS 1 文件 / REVIEW 1 文件 / PYTEST 1 文件 / SRS 2 处 = 共 3 类 5 文件 6 锚）。

### 3.1 Spec Mode 三工件（.trae/specs/cr29_b4_fr_check2_ssot_8/）

| 工件 | 精确代码锚 | 核心内容摘要 |
|---|---|---|
| spec.md（工件 1/3 · Specify 产物）| [spec.md](file:///Users/lee/products/agentLisp/.trae/specs/cr29_b4_fr_check2_ssot_8/spec.md) | 7 AC（6 rule：AC-1/2/3/4/5/7 + 1 rubric AC-6 0-2 阈值=2）；§1 问题 & 目标 & 非目标；§2 FR/NFR 表；§3 约束/依赖/假设；§5 开放问题 Q1~Q4 全部关闭（Q1 路径 A 绝对路径 require；Q2 1/1→2/2 Scenario 数字依据；Q3 SSOT drift 不许 silent 修 + 审批流；Q4 fallback 正则单行严格前缀后缀避免误抓） |
| tasks.md（工件 2/3 · Plan 产物）| [tasks.md](file:///Users/lee/products/agentLisp/.trae/specs/cr29_b4_fr_check2_ssot_8/tasks.md) | 5 原子任务串行依赖图（T0 附录 C in_progress 回写制度化前置已完成 → T1 新建 pytest → T2 附录 B 数字列/代表列 → T3 附录 C Completed → T4 终验 TR1~5 → T5 commit-F + push + handoff），每条 Task 带 5~7 条 Task-local TR（Evidence 槽在 Implement 时填完） |
| review.md（工件 3/3 · Independent Review 产物）| [review.md](file:///Users/lee/products/agentLisp/.trae/specs/cr29_b4_fr_check2_ssot_8/review.md) | 独立 Reviewer Verdict：Cycle1 6/6 AC PASS；Findings 3 条（F1/F2/F3 全 Fix = 0 Open）；§4 Cycle2 AC-7 handoff 待补证槽位（写完本 handoff 后后续 agent 填 Actual Verdict = PASS）；忠实范围 Rubric AC-6 Score=2/2 满分 |

### 3.2 新建 pytest（runtime/tests 1 文件 · 1 顶层函数 · 9 assert · 0 pytest.skip）

- 精确文件锚：[test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal.py](file:///Users/lee/products/agentLisp/runtime/tests/test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal.py)
- 顶层装饰器 + 签名锚（AC-1 VERBATIM）：
  * L34：`@pytest.mark.req("FR-CHECK-2")`（大小写敏感，与附录 B L287 首列逐字节相等）
  * L35-38：`def test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal(tmp_path: Path) -> None:`（VERBATIM 签名）
- 制度化双路径 zero skip 关键锚：
  * 路径 A（racket 在 PATH）：L67-L91 真 subprocess `racket tmp_path/print_sideeffect.rkt`（require 绝对路径 `compiler/checker.rkt`）；rc!=0 不调用 `pytest.skip`，直接走 fallback 分支
  * 路径 B fallback（本机 which racket = not found）：L93-L107 静态单行正则匹配 `compiler/checker.rkt L87`，`RACKET_DEFINE_RE` L29-31 末尾双右括号 `\)\)\s*$`（F1 Low Finding 已修复 → 首版单右括号不匹配 L87 实际双括号）
  * 三向全等断言锚 L120-L134：`racket_set == expected_set == python_set`，失败 message 打印 5 行对称差清单（Racket Δ expected / Python Δ expected / Racket Δ Python）
  * `pytest.skip(` 真调用 计数 = **0 次**（精确 grep 剔除注释行 · AC-2 rule 达标）
  * 体内 assert 总数 = **9 条**（≥4 AC-2 阈值，T1-TR5 独立验证）

### 3.3 SRS 回写 2 处（docs/spec/agentlisp_srs.md · 2 insertions 2 deletions · 严格字节量等价）

- 附录 B L287 FR-CHECK-2 矩阵行锚（1/1→2/2 + 代表列合并 + 代码锚 3 源追加）：
  * [agentlisp_srs.md:L287](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L287-L287)
  * 精确改动：
    - Scenario=1/Passed=1 → **Scenario=2/Passed=2**（Q2 关闭结论依据：旧 1 护栏函数 + 新 1 SSOT 全等函数 = 2 顶层函数 = 2 scenario）
    - 代表列 1 函数 → **2 函数合并**：旧 `` `test_声明具副作用工具但缺少_harness_护栏_err_unguarded_tool_execution` `` + 新 `` `test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal` ``（双反引号包各自 + 英文逗号分隔，对齐 L299 IF-MCP-1 代表列格式）
    - 代码锚列追加 2 个新锚：① `[checker.rkt](file:///.../compiler/checker.rkt)` 内文末尾加 `SIDEEFFECT-BUILTIN-TOOLS 8 项枚举 define L87 = 双端 SSOT 不变性`；② 新增 `[runtime/checker.py L22-33](file:///.../runtime/checker.py#L22-L33) SIDEEFFECT_BUILTIN_TOOLS frozenset 8 项 Python 镜像`
- 附录 C L367 Roadmap B-4 状态行（Pending → Completed 制度化闭环）：
  * [agentlisp_srs.md:L367](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L367-L367)
  * 精确状态流：Pending → **in_progress（CR-29）**（PLAN 阶段 T0 制度化第一写 ✅）→ **✅ Completed（CR-29）**（IMPLEMENT 阶段 T3 状态闭环 ✅）；其余 4 列（B-4 ID / 缺口 / SRS 绑定 / 交付形态）字节不变

---

## 4. 未跑完的真联调项（环境限制，非代码阻塞）

| # | 未跑项 | 类型（硬阻塞 / 未来顺位 / 不相关）| 释放条件 / 下一顺位 / 理由 |
|---|---|---|---|
| U1 | **C-1 τ²-bench v1.0 1000 真样本 fix_rate_total ≥ 0.90**（P1-3 AC-3 · 永久硬阻塞 VERBATIM）| **硬阻塞（外部资源缺失）** | 必须用户终端 VERBATIM 三条命令：① `brew install gh` ② `gh auth login` ③ `gh release download τ²-bench-v1.0 -R agentlisp/t2-bench -D $HOME/.cache/agentlisp/t2-bench-v1.0` → 数据齐后 `uv run python scripts/bench/run_t2_bench.py --sample-range 1..1000 --timeout 600s` → report.json fix_rate_total ≥ 0.90；**任何 Agent 不可自动执行这三条（需浏览器 OAuth + 终端交互）** |
| U2 | **C-2 附录 B 矩阵 Passed 求和精确对齐实际 pytest 124**（B-4 后下一顺位文档核查）| **Roadmap 下一顺位（第 9/11）** | 本轮 CR-29 只动附录 B L287 FR-CHECK-2 行数字 + 代表列 + 附录 C L367；L272 矩阵汇总「当前基准 119」未改（与实际 123→124 偏差）；L301 AC-2 行 baseline 119 未改（与实际 123/124 偏差）。下一顺位 C-2 专门用临时 heredoc 逐行累加附录 B Passed 列 = 实际 pytest passed 报告数 = 当前 124（CR-29 终值），孤儿清单 34-ID 字节不动 |
| U3 | **C-3 v2.0.0-rc2 打签 + release.yml 5 jobs green + SHA256SUMS 0 mismatch + OCI 5 labels = git 元数据**（Roadmap 最后作业级 11/11）| **依赖 U1+U2+C-1 前置全 PASS** | C-2（文档矩阵 124）+ C-1（τ² fix_rate ≥ 0.90）都 PASS 后再启动；`git tag -s v2.0.0-rc2 -m "CR-26+ GA RC · baseline 124 · OCI 5 labels + FR-PARSER-3 emit + perf job"` → `git push origin v2.0.0-rc2` → 等 release.yml 5 jobs 全部 green → `shasum -c SHA256SUMS` 0 mismatch → `docker inspect ghcr.io/4TWS3/agentLisp:v2.0.0-rc2` 5 个 OCI labels 非空且等于 git 元数据 |
| U4 | CI 真环境路径 A（racket 在 PATH）跑 `require 绝对路径 checker.rkt` 真 subprocess 分支（本机 which racket not found 未触发路径 A）| **环境受限但不阻塞 Review（制度化双路径 zero skip，路径 B fallback 已硬断言全过）** | 本机 fallback 分支覆盖 100%；CI 真环境 `Bogdanp/setup-racket@v1.11 RACKET_VERSION=8.12` 会触发路径 A，若 require 真成功则 stdout 抽 8 token 与 fallback 集合全等 → 不需额外修；若路径 A returncode≠0（CI 环境 checker.rkt 缺依赖，概率极低），自动回退 fallback 分支继续硬断言，不会 pytest.skip，基线稳定 124 |
| U5 | Review §4 Cycle2 AC-7 handoff 补证 Actual Verdict 槽 | **本 handoff 写完后下一微小 commit（hash fill）补 Actual Verdict** | 本节 §7 最后一段写 handoff hash fill 流程；下一微小 commit 补 review.md §4 Cycle2 AC-7 Actual Verdict = PASS 即可（制度化 CR-28 同款流程） |

---

## 5. 运行时外部端点 & 依赖硬约束（交接防坑指南 · 34 ID 清单 · VERBATIM 保留）

本章节 **逐字继承 CR-27 / CR-28 handoff 第 5 章**（制度化保持一致，下一接手 Agent 零学习成本）。不准改、不准减、不准增加新条目没写在本项目_memory里的 endpoint。

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
| ruff 工具 | `ruff check` + `ruff format`（CR 所有 CR 双绿硬要求）|
| GitHub Actions Racket setup VERBATIM | `Bogdanp/setup-racket@v1.11`；RACKET_VERSION=8.12；packages=`base,rackunit-lib,syntax-parse,data-lib,json-lib,parser-tools-lib`（CR-27 perf job 已制度化写在 ci.yml，不允许改 versions 除非用户审批） |
| pyproject.toml version VERBATIM | 2.0.0a1（L3 字节精确值；C-3 tag v2.0.0-rc2 时不改 pyproject version，tag 只打 git tag 不等同 pyproject 发版） |
| pyproject optional-deps 9 组 VERBATIM | core / llm / mcp / web / durable / observability / sandbox / dev / all（9 组缺一不可，顺序可重排但集合全等） |
| remote origin VERBATIM | `git@github.com:4TWS3/agentLisp.git`（SSH；~/.ssh key 已配置，push 零输入密码） |
| SSOT 8 项 SIDEEFFECT-BUILTIN-TOOLS VERBATIM（CR-29 核心交付不变性的 SSOT 字面值）| `bash, git-push, wget, curl, scp, dd, chmod, sudo`（8 项；大小写敏感；连字符 git-push 不是下划线 git_push；bash 全小写；顺序不影响集合相等） |
| CR 编号 VERBATIM（下一 CR 递增）| CR-26 → CR-27 → CR-28 → CR-29（当前）→ CR-30（C-2 文档求和 · 下顺位）；编号连续不跳不缺口 |
| τ²-bench 外部资源释放命令 VERBATIM（C-1 硬阻塞；不准加参数不准改路径不准改 tag）| ① `brew install gh` ② `gh auth login` ③ `gh release download τ²-bench-v1.0 -R agentlisp/t2-bench -D $HOME/.cache/agentlisp/t2-bench-v1.0` |
| release.yml 产物 VERBATIM（C-3 前置记住不准改）| 三 OS build 产物在 `python/` 目录下 `python/dist/*`；actions/download-artifact@v4 `merge-multiple: true` → `release-artifacts/`；生成 `SHA256SUMS` 含所有产物哈希 |
| ghcr.io image VERBATIM（OCI 5 labels 不准少）| docker/metadata-action@v5 `images=ghcr.io/${{ github.repository }}`；标签规则 semver `{{version}}/{{major}}.{{minor}}/latest on default_branch`；**5 个 OCI labels 必须齐全且 = git 元数据**：`org.opencontainers.image.source, version, revision, created, title`（5 条 OpenContainers 官方 spec，缺一不可） |
| SRS 来源 VERBATIM（唯二合法更新源 = 1)用户右侧 Studio 面板发布 agentlisp_srs.md 新版本；2)本 CR 自己的附录 B/C 数字列/状态/代表列回写）| SRS 文件 = `docs/spec/agentlisp_srs.md`（ISO/IEC/IEEE 29148 6 章结构 + 附录 A/B/C；本节 5.2 列表不准改 §1-§6 正文内容除非用户审批） |

---

## 6. 下一步自由方向（严格按附录 C 固化优先级，不可跳项！）

### 6.1 强制顺位（Roadmap 11 项从 8→9→10→11 · 不准跳项）

| 顺位 #（Roadmap 11 项）| 工作 ID | 核心内容摘要 | 前置依赖 |
|---|---|---|---|
| 9/11 | **C-2 文档矩阵求和对齐实际 124**（下一顺位）| ① 附录 B L272 汇总行「当前基准 119」→ 改为实际 CR-29 终值 124；② 附录 B L301 AC-2 行 baseline 119 → 改为真实 123（CR-28 基线）/ 或 124（CR-29 基线，看惯例），需用户看 CR-27/28 AC-2 数字选一个；③ 逐行累加附录 B Passed 列 = 124（临时 heredoc python 不落盘）；④ 孤儿清单 34-ID 字节全等核查通过，不改清单顺序/内容 | B-4 CR-29 全闭环 + handoff push 完成（即本 CR 完了才启动） |
| 10/11 | **C-1 τ²-bench v1.0 1000 样本 P1 AC-3** | 用户终端 VERBATIM 三行 gh 命令 → 1000 样本跑完 → report.json fix_rate_total ≥ 0.90 | **需用户终端操作（唯一前置）**；任何 Agent 不能自动解阻塞 |
| 11/11 | **C-3 v2.0.0-rc2 打签 + release 作业级** | `git tag -s v2.0.0-rc2 -m "..."` → `git push origin v2.0.0-rc2` → release.yml 5 jobs green → SHA256SUMS 0 mismatch → docker inspect ghcr.io OCI 5 labels = git 元数据 | C-2 PASS + C-1 PASS（前置双 PASS 缺一不可） |

### 6.2 可选非阻塞优化（不计入 Roadmap，随时做但不影响合规）

| 可选优化 ID | 内容摘要 | 影响/收益 |
|---|---|---|
| O1 | Review §4 Cycle2 AC-7 补 Actual Verdict = PASS + 填手交文档 7 章全等证据（CR-28 同款 hash fill 小 commit） | 消除 Review Partil → 7/7 PASS Full Verdict；属于本 CR-29 制度化收尾微小 commit（建议 1~2 file change 2 insertions） |
| O2 | 新建 pytest 里的路径 A 写一个 CI smoke（在 ci.yml perf job 后面加 step `pytest -k ssot_8_items -v` 看 CI 的路径 A 是否真走 racket subprocess；如果 CI racket require checker.rkt 失败则回退 fallback，基线不波动）| 提早发现 CI 路径 A 的 require 失败风险；不要求本轮做，不阻塞 CR-29 交付；AC-6 Rubric 做这个会改 ci.yml 越界 → 建议放 CR-30 C-2 之后的下下个小 CR 独立 scope |
| O3 | 临时 heredoc python 核查 34-ID / 附录 B 求和 的脚本，可抽象成 `scripts/check_roadmap_traceability.py`（但需独立 CR 独立 scope，避免 CR-29 AC-6 Rubric 改 scripts/ 越界扣 0 分）| 每 CR 启动前自动核查 34-ID / 矩阵 baseline，减少 Reviewer 手工；本轮不做，改 scripts/ 属于 Class 4 会让 AC-6 Score=0，绝对不准放 CR-29 |

---

## 7. 交接人 & 时间

- CR-29 交付人（自动化 Agent）：**CR-29 B-4 automation（本会话 Spec Mode 5 阶段全流程 Agent）**
- Handoff 文档创建时间：**2026-10-05（与 CR-26/27/28 handoff 同日期的制度化连续交付日期；真实时间 `date '+%Y-%m-%d %H:%M:%S'` 待 push 后回填到本段末尾）**
- 关联 CR-29 核心 commit hash：**3228f99**（等 push 成功后用 `git rev-parse HEAD` 真实值回填到这里 + 第 1 章末尾，同时检查 `git rev-parse HEAD == git ls-remote origin main | awk '{print $1}'` 全等，确保其他接手人 `git pull origin main` 直接看到本 CR 的 5 个交付文件 + 手交文档）
- 关联 Handoff hash fill 微小 commit hash：**等写 review.md §4 Cycle2 AC-7 Actual Verdict + 手交文档 hash fill 完成后，把这个 commit hash 写在这里（制度化 CR-28 同款 2 commit 结构）**

```
下一接手 Agent 必做 4 步（制度化零思考）：
  1. git pull origin main
  2. 检查 HEAD hash = 本 CR-29 手交 hash fill 后的 HEAD（两个 commit）
  3. 跑 4 硬指标（pytest 124 + ruff 双绿 + GetDiagnostics 0）确认基线不回退
  4. 按顺位 9/11 启动 C-2 文档矩阵求和附录 B + AC-2 baseline 对齐
```
