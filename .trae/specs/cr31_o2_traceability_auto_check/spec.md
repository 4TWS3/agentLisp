# CR-31 O2 路线图可追溯性自动化核查脚本（scripts/check_roadmap_traceability.py + CI 门禁）

- **CR 编号**：CR-31（Roadmap 附录 C 额外任务 · O2 类，非 11 项必达，不影响 C-1/C-3 顺位）
- **基线 HEAD**：390d331；本 CR 严格基线目标 124 → 127 passed（新增 3 pytest smoke）
- **核心目的**：把 CR-26~CR-30 每轮手工 heredoc Python 核查（34-ID 三集合全等 + 附录 B 基线整数五向全等 + 32 行非汇总 80 不变）固化为正式脚本，加入 `ci.yml python-tests` job 每 CR 自动门禁，消除 Reviewer 手工核查成本。

---

## §1 问题 · 目标 · 非目标

### 1.1 问题陈述（Evidence）
- CR-28/29/30 每轮 Reviewer 必须复制粘贴 **80+ 行 heredoc Python** 独立核查 34-ID 三集合全等（孤儿 L315 = 附录 B 首列 = 正文词边界命中）、附录 B Passed 求和与 pytest 实际的整数对齐、32 行非汇总场景合计=80；每次耗时 2~3 分钟且手误概率高
- [ci.yml python-tests:L209-L214](file:///Users/lee/products/agentLisp/.github/workflows/ci.yml#L209-L214) 已有 traceability matrix 生成步骤，但**缺合规性门禁**（只生成，不校验漂移）；一旦有 Agent 误改附录 B 数字列/孤儿清单，CI 不会 fail
- [agentlisp_srs.md L312-L316](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L312-L316)「自动化维护脚本」章节已声明 `bdd_export_traceability.py` 但未声明路线图合规核查脚本

### 1.2 目标（成功判据 = 7/7 AC PASS）
1. **脚本落地**：`scripts/check_roadmap_traceability.py` 可独立运行（无外部依赖，只使用 Python 3.11+ stdlib + 读取本地 SRS.md + junitxml 可选）
2. **3 类核查覆盖**：ID 全等 / 基线整数对齐 / 32 行非汇总场景=80，每类失败 exit=1 且 stderr 前缀严格可 grep
3. **pytest smoke ≥3**：合法场景 exit=0 / 构造 ID 漂移 exit=1 / 构造基线错误 exit=1，严格基线 +3
4. **CI 门禁**：`ci.yml python-tests` ubuntu-latest 在 traceability matrix 生成步骤之后插入新 step，失败即 job fail

### 1.3 非目标（Not In Scope · AC-6 Rubric 扣分项边界）
- ❌ 不修改 `docs/spec/agentlisp_srs.md` 正文 §1~§6 / 附录 B 数字列（除制度化 T0 第一写「附录 C 追加额外任务行」外，不准动附录 B/C 的任何数字或状态）
- ❌ 不新增 / 修改 `runtime/`、`compiler/`、`host/` 下任何文件；不动 pyproject.toml、Dockerfile、release.yml
- ❌ 不修改 `bdd_export_traceability.py` 的既有行为（本脚本 = 独立互补，零侵入姐妹脚本）
- ❌ 不实现自动修复（fix 模式）：只报告失败，不写回 SRS.md

---

## §2 功能需求（FR）& 非功能需求（NFR）表

| # | 类型 | 标题 | 规格（VERBATIM）|
|---|---|---|---|
| FR-1 | FR | CLI 接口 & exit 编码 | **无位置参数必选**；可选：`--srs PATH`（默认 `docs/spec/agentlisp_srs.md`）、`--pytest-junitxml PATH`（CI 已有 junit 时读此文件获取 `tests=` 实际 passed 数；缺失则 fallback 到 `PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -q --no-header -p no:cacheprovider runtime/tests scripts/tests host/tests` 子进程实际跑并解析尾行整数）、`--strict-baseline N`（可选，强制预期 pytest passed=N，缺失则从 SRS L274 摘要行解析）。exit=0 全过；exit=1 任一核查失败；stderr 每条失败行前缀严格 ∈ {`ROADMAP-ID-MISMATCH:`, `ROADMAP-BASELINE-MISMATCH:`, `ROADMAP-SCENARIO-SUM-MISMATCH:`}，不准出现裸 print 无前缀错误 |
| FR-2 | FR | 34-ID 三集合全等核查 | ① 孤儿集 = 解析 SRS.md 中「### 孤儿需求核查」后一行 SRS-ID 列表（L315=34-ID 清单行），按 `, ` 切分 + strip；② 附录 B 首列 = SRS.md「## 附录 B」后表格中首列 ID，正则：`^\|\s*(\*\*?[A-Z][A-Z0-9-]+(?:[a-z])?\*\*?|[A-Z][A-Z0-9-]+(?:[a-z])?)\s*\|`（兼容粗体/非粗体；ID_RE 末尾允许 [a-z]? 以匹配 NFR-PERF-1a/1b/SEC-1a/1b/1c）；③ 正文命中集 = SRS.md 去除「## 附录 B」及之后内容后，对 ID_RE 词边界匹配；**三集合必须全等（差集全空 & len=34）**，失败输出 `ROADMAP-ID-MISMATCH: set(orphan-AppB)=X set(AppB-orphan)=Y set(orphan-body)=Z set(body-orphan)=W union=U`；父标题 NFR-PERF-1 伪命中必须主动 discard（不准计入 body_ids）|
| FR-3 | FR | 基线整数五向全等核查 | ① v1 = 从 L274 摘要行正则 `pytest (\d+) passed` 提取整数；② v2/v3 = 附录 B AC-2 汇总行（`| **AC-2** |` 开头）第 3 列 Scenario 数 + 第 4 列 Passed 数（两列必须相等）；③ v4 = 从 `--pytest-junitxml` 解析 `<testsuite tests="N">` 或 `@tests` 属性求和 / 或 fallback pytest 子进程尾行 `(\d+) passed`；④ v5 = `--strict-baseline N` 传值（缺失则 = v1，不做五向 → 退化为四向）。**四向或五向整数必须全等（set size=1 & 值=v1）**，失败输出 `ROADMAP-BASELINE-MISMATCH: L274=X AC2_scn=Y AC2_pas=Z actual=W [strict=N] union_size=S` |
| FR-4 | FR | 32 行非汇总 Scenario/Passed 合计核查 | 附录 B 表格中 **排除 AC-2 汇总行**（首列=AC-2）和 **排除表头/分隔线/汇总空行** 后，剩余 32 行（L278~L299 + L302~L311 范围，1-indexed）：① Scenario 列合计 = S_sum（应 = 80，但不硬校验允许 ±2 增长，报告警告即可，不 fail）；② Passed 列合计 **必须 = S_sum（Scenario=Passed 即每条场景全通过，不准 Fail/Skip 出现在 32 行非汇总）**；③ fail 时输出 `ROADMAP-SCENARIO-SUM-MISMATCH: rows=32? ScnSum=X PasSum=Y expect_PasSum==ScnSum (fail_on_diff=true)` |
| NFR-1 | NFR | 零外部依赖 + 秒级完成 | `import` 只允许 stdlib（re/pathlib/sys/argparse/subprocess/xml.etree.ElementTree/dataclasses/typing），不准 import runtime/scripts 内部模块；SRS.md=800 行时，**单次运行 wall-clock < 0.3s（不含 fallback pytest 子进程）** |
| NFR-2 | NFR | pytest 基线增长精确 = 3 | 新增 `scripts/tests/test_check_roadmap_traceability.py` = 3 用例（合法/ID 漂移/基线错误），严格基线 CR-30 终值 124 → CR-31 终值 **127 passed**，不准 Δ≠3 |

---

## §3 约束 · 依赖 · 假设（CDA）

| # | 类别 | 内容 |
|---|---|---|
| C1 | 约束 | **不动 [agentlisp_srs.md L274-L376](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L274-L376) 的任何数字或状态**；除制度化 T0 第一写在「附录 C 末尾」新增 1 行「额外任务」（ID=CR-31=O2，状态 in_progress）外，其他零改动；否则 AC-6 直接 0 分 |
| C2 | 约束 | CI step **只在 python-tests ubuntu-latest 执行**（matrix.os == 'ubuntu-latest' 时），Windows 不执行（WSL/Git Bash path 分隔符兼容问题非核心）；step 插入位置：[ci.yml L214](file:///Users/lee/products/agentLisp/.github/workflows/ci.yml#L214-L214) 之后、L216 Upload coverage 之前 |
| C3 | 约束 | 失败 stderr 三条前缀 **精确大小写 + 冒号结尾**，不准新增前缀不在 FR-1 枚举内的错误；否则 CI grep ROADMAP-* 作为门禁聚合时漏算 |
| D1 | 依赖 | fallback pytest 子进程路径 = 与 CR-30 终值 [handoff §2 指标 1](file:///Users/lee/products/agentLisp/docs/handoff/20261005_cr30_c2_traceability_matrix_align_124_handoff.md#L31-L31) VERBATIM 命令字串一致（ENV 前缀 + 参数 7 项全等） |
| A1 | 假设 | SRS.md 附录 B 表结构稳定：7 列 `|---:|` 数字列右对齐；`| **AC-2** |` 汇总行唯一；孤儿清单行 L315 格式稳定（逗号 + 空格分隔） |
| A2 | 假设 | 32 行非汇总的「行数 32」允许 ±1 合法波动（未来 CR 新增非汇总行时，脚本应打印警告但不强制 fail；fail 条件只触发 Scn≠Pas 场景） |

---

## §4 开放问题 Q1~Q4（全部关闭，不影响 Implement）

| # | 问题 | 关闭结论（不允许 open question 进入 Implement 阶段）| 依据 / 决策理由 |
|---|---|---|---|
| Q1 | junitxml `tests=` 属性 vs pytest 尾行整数的优先级？| **junitxml 优先**（CI 有 junit 时零子进程开销）；缺失 junit 才子进程 pytest；都缺失时 FR-3 核查 SKIP 不 fail（stderr warn 绿色不阻塞）| CI 运行成本敏感；本地 Agent 跑脚本能取到 junit 更快 |
| Q2 | 32 行数校验硬 fail 还是 warn？| **行数 warn、Scn≠Pas 才硬 fail**；未来 Agent 新增非汇总行是合规行为（如 AC-1 的 RackUnit 补齐），不应被行数硬锁 | A2 假设 + CR-26/29 都新增过行 |
| Q3 | 34-ID 集合大小 34 是否硬锁？| **集合大小硬锁 34，不准 33/35**；未来新增 SRS-ID 时必须先手工改 SRS 孤儿清单 L315 + 附录 B + 正文三处 → 脚本才会通过（防漂移设计）| ISO 29148 §8.3 完备性要求；孤儿清单 34 是 CR-26 基线不动点 |
| Q4 | 脚本是否需要 `--verbose` 打印成功集合大小？| **不加 verbose**：成功时 stdout 必须空（零噪声），只 exit=0；失败才 stderr 前缀行；符合 CI step 收敛输出惯例 | Unix 哲学：成功静默、失败大声 |

---

## §5 验收标准（Acceptance Criteria · 6 rule + 1 rubric = 7 AC，AC-6 唯一 rubric）

### §5.1 AC 明细（每条必须独立可复现，不准依赖 Implementer stdout）

| AC# | 类型 | 独立复现命令（VERBATIM · Reviewer 原样跑） | 预期结果（PASS 判据） | SRS/NFR 绑定 |
|---|---|---|---|---|
| **AC-1** | `rule` | `ls -la scripts/check_roadmap_traceability.py && head -1 scripts/check_roadmap_traceability.py \| grep -E '^#!|from __future__' && uv run python scripts/check_roadmap_traceability.py --help 2>&1 \| grep -E -- '--srs\|--pytest-junitxml\|--strict-baseline'` | ①文件存在且可执行权限≥644；②首行 shebang 或 `from __future__ import annotations` 合规；③ --help stdout 三参数全出现（三个 grep 命中 ≥1 次 each） | FR-1 CLI 三参数 |
| **AC-2** | `rule` | `uv run python scripts/check_roadmap_traceability.py; echo "EXIT=$?"`（**当前 HEAD 390d331，无参数，本地无 junit**）| ① EXIT=0（34-ID 全等 + 32 行 Scn=Pas 均过；基线四向因无 junit fallback pytest 子进程实际跑 124 → v4=124 = L274 v1=124 = AC2 v2/v3=124 → PASS）；② stdout 空；③ stderr 0 行（无 ROADMAP-前缀错误）| FR-2 + FR-3 + FR-4 三条核查当前基线均合法 |
| **AC-3** | `rule` | `sed 's/FR-PARSER-1, FR-PARSER-2/FR-PARSER-1, FR-PARSER-2, FAKE-ID-999/' docs/spec/agentLisp_srs.md > /tmp/srs_drift_id.md && uv run python scripts/check_roadmap_traceability.py --srs /tmp/srs_drift_id.md; echo "EXIT=$?"; echo "STDERR grep:"; uv run python scripts/check_roadmap_traceability.py --srs /tmp/srs_drift_id.md 2>&1 >/dev/null \| grep -c '^ROADMAP-ID-MISMATCH:'` | ① EXIT=1；② grep count = 1（精确 1 条 ID 漂移错误）；③ stderr 不准出现 `ROADMAP-BASELINE-MISMATCH:` 或其他前缀（证明 FR-2/FR-3/FR-4 独立失败互不干扰）| FR-2 ID 漂移失败语义 |
| **AC-4** | `rule` | `sed 's/pytest 124 passed/pytest 119 passed/' docs/spec/agentlisp_srs.md > /tmp/srs_drift_baseline.md && uv run python scripts/check_roadmap_traceability.py --srs /tmp/srs_drift_baseline.md --strict-baseline 124 2>&1 >/dev/null; echo "EXIT=$?"; uv run python scripts/check_roadmap_traceability.py --srs /tmp/srs_drift_baseline.md --strict-baseline 124 2>&1 >/dev/null \| grep -c '^ROADMAP-BASELINE-MISMATCH:'` | ① EXIT=1；② grep count = 1；③ stderr 不准出现 `ROADMAP-ID-MISMATCH:`（L274 改 119 与 AC-2=124 冲突，触发基线错误，但 ID 三集合仍合法 = 无 ID 漂移错误） | FR-3 基线整数冲突失败语义 |
| **AC-5** | `rule` | `PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest tests/test_check_roadmap_traceability.py -v -p no:cacheprovider --strict-markers 2>&1 \| tail -15` | ① 3 passed（名字分别含 `legal_exit_zero`、`id_drift_exit_one_prefix_count_one`、`baseline_mismatch_exit_one_prefix_count_one`，不准多/少）；② CR-30 基线 124 + 本脚本 3 → 全仓严格模式跑 `pytest -q` 尾行 = **127 passed / 1 skipped / 1 warning**（Δ=+3 精确） | NFR-2 基线增长精确 = +3 |
| **AC-6** | **rubric · 0-2 分 · 阈值=2** | 独立 reviewer 手工核查三类：① `git diff --name-only HEAD`（除 SRS.md T0 制度化追加 1 行外，文件集合 ⊆ {scripts/check_roadmap_traceability.py, tests/test_check_roadmap_traceability.py, .github/workflows/ci.yml, .trae/specs/cr31_*/*}；② 总 insertions+deletions（不含 .trae/specs/）≤ 200 行；③ grep `docs/spec/agentlisp_srs.md` 所有改动行正则只匹配 `类别 D` / `可选优化池` / `额外任务` / `in_progress（CR-31）`，不准匹配 L274/301/315/376 的数字列或状态列 | Score=**2/2 满分**（三条件全满足）→ PASS；Score=1（违反 1 条但不影响功能）→ 需 Remediation；Score=0（违反 ≥2 条 或 触碰 runtime/compiler/host 任一）→ 直接 Review FAIL，退回 Implement | C1 约束硬执行 |
| **AC-7** | `rule` | `grep -n -A 10 'check_roadmap_traceability' .github/workflows/ci.yml \| head -15` | ① 存在 `scripts/check_roadmap_traceability.py` 调用行；② 该 step `if: matrix.os == 'ubuntu-latest'`（C2 约束）；③ 该 step 位于「Generate traceability matrix」之后、「Upload coverage」之前（行序符合 C2）；④ 无 `continue-on-error: true`（失败必须硬 fail job）| C2 + CI 门禁生效 |

### §5.2 非法构造边界（AC-3/AC-4/AC-5 必须覆盖的负例）
- ID 漂移负例不准使用「删除附录 B 行」构造（会影响行数 & 场景合计，造成多因混杂）；必须用 [sed 孤儿清单尾部追加 FAKE-ID](file:///tmp/srs_drift_id.md) 方式（只影响孤儿集合，不影响附录 B / 正文，差集精确单点）
- 基线错误负例不准使用「改 AC-2 汇总行」构造（会同时影响 FR-3 v2/v3 → union_size 仍 1 伪 PASS）；必须用 [sed 改 L274 摘要 124→119](file:///tmp/srs_drift_baseline.md) + `--strict-baseline 124` 双输入方式（v1=119 vs strict=124 vs AC2=124 vs actual=124 → 冲突集合 size≥2 → 硬 fail）

---

## §6 交付物清单（4 类 + T0 制度化 1 类，共 5 文件；与 AC-6 Rubric 集合全等）

| # | 路径 | 类别 | AC# 覆盖 |
|---|---|---|---|
| 1 | `scripts/check_roadmap_traceability.py` | 核心脚本 | AC-1 / AC-2 / AC-3 / AC-4 |
| 2 | `tests/test_check_roadmap_traceability.py` | pytest smoke 3 用例 | AC-5 |
| 3 | `.github/workflows/ci.yml` | python-tests ubuntu 新 step 插入 | AC-7 |
| 4 | `.trae/specs/cr31_o2_traceability_auto_check/{spec.md,tasks.md,review.md}` | Spec Mode 三工件（本 spec.md = 工件 1）| — |
| 5 | `docs/spec/agentlisp_srs.md 附录 C 末尾新增额外任务行 1 行` | 制度化 T0 第一写（Plan 阶段必做，Implement 不回写数字列）| AC-6（AC-6 的「除 T0 追加 1 行外」豁免条件）|

---

**AC 计数**：6 条 rule（AC-1/2/3/4/5/7）+ 1 条 rubric（AC-6 阈值=2）= **7/7 AC**，结构与 CR-30 spec.md 完全全等（制度化 grep `^| AC-#` diff 空）。
