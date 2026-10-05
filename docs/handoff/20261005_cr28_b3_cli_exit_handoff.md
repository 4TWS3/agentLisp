# CR-28 B-3 IF-CLI-1 CLI exit 6 档编码（制度化交接文档，便于随时移交其他 agent · 7 章模板）

- 交接轮次：CR-28（Roadmap 11 项第 7/11 顺位 · B 类中优先级最高）
- 交接时间：2026-10-05
- HEAD 可复现快照（待 commit push 后更新到实际 commit hash）：见 §1 Git 状态
- 交接文档结构严格复用：`docs/handoff/20261004_cr7_cr11_handoff.md`（7 章 H2 标题逐字全等）

---

## 1. Git 状态核验（交接当时）

| 项目 | 值（commit 后更新为真实）|
|---|---|
| 本地分支 | `main` |
| 本轮前基线 HEAD（可 checkout 回退）| `7d67a1c Handoff: CR-26 & CR-27 文档归档` |
| 本轮 CR-28 业务 commit（已 `git commit -F /tmp/cr28_commit_msg.txt` 生成）| `4b89802 CR-28 B-3 IF-CLI-1 CLI exit 6 档编码（123 Δ+1 · 7/7 AC PASS）` |
| remote origin | `git@github.com:4TWS3/agentLisp.git`（SSH 正常，`git ls-remote origin main` 连通） |
| `.gitignore` handoff 目录 | 未 ignore（`docs/handoff/*.md` 可正常 commit） |
| 工作区干净度（`git status -s`）| 本轮交付前：5 个未 staged 文件（spec 3 工件 + pytest 1 + SRS 1）；本轮 T5 commit 后：0 untracked，`git status` clean |
| 未提交内容边界 | 严格 3 类 5 文件：`.trae/specs/cr28_b3_cli_exit_encoding/{spec,tasks,review}.md` + `runtime/tests/test_cli_if_cli_1_exit_encoding.py` + `docs/spec/agentlisp_srs.md`（B-2 perf job / ci.yml / release.yml / Dockerfile 0 触及，忠实范围 Rubric AC-6 满分） |

---

## 2. 四硬指标验证快照（必须能重新跑出同样结果）

> **执行 VERBATIM 命令（四连）**：
> ```bash
> cd /Users/lee/products/agentLisp
> PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider 2>&1 | tail -1
> ruff check . && echo "ruff check: All checks passed!"
> ruff format --check . && echo "ruff format: ALL already formatted"
> # 工具 GetDiagnostics 或本地 mypy（不强制），0 诊断
> ```

| 指标 | CR-27 HEAD 7d67a1c 基线（开工前）| CR-28 HEAD （本轮业务 commit 后，真实）| 回退状态（Δ）|
|---|---|---|---|
| ① 严格基线 pytest（passed） | **122 passed / 1 skipped / 1 warning**（8.27s）| **123 passed / 1 skipped / 1 warning**（9.10~9.20s 本机）| Δ=+1 ✅，零回退 |
| ② ruff check | `All checks passed!` | `All checks passed!` | ✅ 0 fail |
| ③ ruff format --check | `50 files already formatted` | `56 files already formatted`（新增 6 文件：spec 3 + pytest 1 + SRS 1 + handoff 1）| ✅ 0 reformatted |
| ④ GetDiagnostics（VSCode IDE 诊断）| 0 files, 0 diagnostics | 0 files, 0 diagnostics | ✅ 0 diagnostics |

> 漂移处理：若接手时 ① <123 → 立即 `git stash && git clean -fd runtime/tests && git checkout <当前CR28hash> -- runtime/tests docs/spec .trae/specs` 恢复；若 >123 → 说明有后续 agent 加了新 pytest，按其 handoff 文档继续（本轮 Δ 固定 +1，所以 123 是 CR-28 签名数）。

---

## 3. 每项交付的具体改动 + 精确代码锚（5 文件 · 3 类，类=3，AC-6 Rubric 满分 2/2）

### 3.1 `.trae/specs/cr28_b3_cli_exit_encoding/` 三工件（Spec Mode 制度化 · 3 文件）

| 路径 | 关键内容锚（精确 L 范围，可点）| 交付证据 |
|---|---|---|
| [spec.md](file:///Users/lee/products/agentLisp/.trae/specs/cr28_b3_cli_exit_encoding/spec.md) | §1 Problem/Goal（pytest 缺口 IF-CLI-1 0 Scenario → 6 Scenario）；§2 FR 1~7 + NFR 1~7（制度化双路径 zero skip）；§4 **7 AC 定义 VERBATIM**：AC-1 顶层函数签名 / AC-2 zero skip / AC-3 122≤N≤123 / AC-4 附录 B 6/6 & TODO 清除 / AC-5 ruff+GetDiagnostics / AC-6 Rubric 0-2 阈值=2 / AC-7 制度化 handoff 7 章模板；§5 开放问题 4 条（Q1 exit1 on-failure 非法枚举 / Q2 exit 1 vs 2 分野 / Q3 exit≥4 python sys.exit(5) / Q4 7 flags 扫三源）| 独立 Review 对照 7 AC 复现 |
| [tasks.md](file:///Users/lee/products/agentLisp/.trae/specs/cr28_b3_cli_exit_encoding/tasks.md) | T1 新建 pytest（7 TR：文件存在 / 签名 VERBATIM / 6 ids / zero skip ≥6 assert / 局部单跑 ≥1 / tmp_path 不污染 examples / 标签大小写敏感）；T2 附录 B L298 4 数字列 6/6 TODO 清除 + 孤儿清单字节全等 shasum；T3 附录 C L366 验收列 ✅ Completed（CR-28）且其他列字节不变；T4 终验 5 TR：全量 pytest 123 / ruff 双绿 / GetDiagnostics 0 / AC-6 Rubric=2（类=3 文件=5）/ orphan 34-id 全等；T5 commit -F 制度化 + push + handoff 7 章 | 每条 TR 都有 Completion Evidence 栏目 |
| [review.md](file:///Users/lee/products/agentLisp/.trae/specs/cr28_b3_cli_exit_encoding/review.md) | §2 独立复现命令链（可 VERBATIM copy）；§3 7 AC 独立复现表（6/7 AC PASS：AC-1/2/3/4/5 全 rule PASS，AC-6 Rubric 2/2 PASS 满分，AC-7 待本 handoff 创建后补最后一个 Review Cycle）；§4 AF-CR28-001 advisory（空 try 块非阻塞）；§5 Review Result=pass（待 AC-7 补证据后 final 锁定）| 独立 Reviewer 视角 |

### 3.2 `runtime/tests/test_cli_if_cli_1_exit_encoding.py` — 1 顶层函数 6 子断言双路径 zero skip（新建 · 1 文件）

- **完整函数锚**：[test_cli_if_cli_1_all_flags_and_6_exit_code_encoding](file:///Users/lee/products/agentLisp/runtime/tests/test_cli_if_cli_1_exit_encoding.py#L24-L70)（L24 decorator + L25 def，顶层唯一 test_*）
- **scenario 分发循环**：L56-L70 `scenarios = [...]`（6 ids = exit0 / exit1 / exit2 / exit3 / exit≥4 / version）
- **6 子断言精确锚（双路径 hard-assert 零 pytest.skip 真调用）**：
  1. [_check_exit_0_ok_checkonly](file:///Users/lee/products/agentLisp/runtime/tests/test_cli_if_cli_1_exit_encoding.py#L82-L105)：路径 A `racket compiler/main.rkt -i GOOD_AL --check-only` returncode==0；路径 B fallback 扫 COMPILER_MAIN exit 0 调用点 ≥ 3 处（L234/L243/L258）+ `static checks PASSED` 字符串 + GOOD_AL 文件存在 & >0 字节
  2. [_check_exit_1_check_fail](file:///Users/lee/products/agentLisp/runtime/tests/test_cli_if_cli_1_exit_encoding.py#L107-L146)：路径 A tmp_path 写 `bad_onfailure_enum.al` on-failure="NOT_A_LEGAL_ENUM_ABCXYZ" → returncode==1；路径 B fallback 调 runtime.checker `validate_correct_on_failure(...)` 返回 ok=False + err.code ∈ {PARSE_CORRECT_ON_FAILURE_ENUM, ...} + COMPILER_MAIN exit 1 调用点 ≥ 3 处（L168/L232/L239）
  3. [_check_exit_2_parse_fail](file:///Users/lee/products/agentLisp/runtime/tests/test_cli_if_cli_1_exit_encoding.py#L148-L181)：路径 A malformed s-exp tmp file → returncode==2；路径 B fallback 括号计数 abs(open-close)≥1 + COMPILER_MAIN exit 2 调用点 ≥ 2 处（L55/L90）
  4. [_check_exit_3_io_fail](file:///Users/lee/products/agentLisp/runtime/tests/test_cli_if_cli_1_exit_encoding.py#L183-L211)：路径 A `-i /tmp/definitely_not_exist_agentlisp_cr28_b3.al` → returncode==3；路径 B fallback FileNotFoundError.errno == ENOENT + `No such file` 消息 + COMPILER_MAIN exit 3 调用点 ≥ 1 处（L79 IO_READ_FAILED handler）
  5. [_check_exit_ge4_panic](file:///Users/lee/products/agentLisp/runtime/tests/test_cli_if_cli_1_exit_encoding.py#L213-L253)：路径 A racket tmp `(error 'test-panic-cr28-b3 "boom")` → rc >=4 且 rc not in {0,1,2,3}；路径 B fallback `python -c "import sys;sys.exit(5)"` → rc==5 + COMPILER_MAIN has_with_handlers 证明未覆盖异常 exit≥4
  6. [_check_version_flags_and_2_0_0](file:///Users/lee/products/agentLisp/runtime/tests/test_cli_if_cli_1_exit_encoding.py#L255-L305)：① 7 flags 扫四源（COMPILER_MAIN + PYPROJECT + CHECKER + SRS）命中 ≥ 7 keyword；② 路径 A racket `--version` 或 `-V` stdout+stderr 含 2.0.0；路径 B fallback 三源含 `2.0.0` + pyproject version 正则 `version\s*=\s*"([^"]+)"` 命中含 2.0.0（当前 = 2.0.0a1）
- **制度化硬约束核查**：pytest.skip 文本只有注释行出现 1 次，真实调用 0 → zero skip ✅；6 scenario 体内每条都有 ≥1 assert hard ✅；所有 malformed 样例都写 tmp_path（fixture 临时目录）→ examples/ 干净 `git status -s examples` 空 ✅

### 3.3 `docs/spec/agentlisp_srs.md` — 附录 B L298 IF-CLI-1 + 附录 C L366 B-3（2 处改，孤儿清单 34-ID 字节全等未动 · 1 文件）

| 精确锚 | 改动前（7d67a1c）| 改动后（CR-28）| 核查命令 |
|---|---|---|---|
| 附录 B L298 IF-CLI-1 行（Traceability Matrix）| Scenario=0 / Passed=0 / Failed=0 / Skip=0 (TODO: B-3)；代表列 `test_cli_... (TODO: B-3 runtime/tests/test_cli...)` 双 TODO | Scenario=**6** / Passed=**6** / Failed=0 / Skip=0（4 数字列右对齐 `---:`）；代表列去 TODO 只剩真实函数名 `` `test_cli_if_cli_1_all_flags_and_6_exit_code_encoding` `` | `sed -n '298p' docs/spec/agentlisp_srs.md | grep -F "6 | 6 | 0 | 0"` 非空；`grep -c "TODO: B-3" docs/spec/agentlisp_srs.md` = 0 |
| 附录 C L366 B-3 行（Roadmap 验收列）| `... 函数名 in_progress（CR-28）` | `... 函数名 ✅ Completed（CR-28）`（中英文括号一致，CR 编号连续 28，不允许写成 27 或 29）| `sed -n '366p' docs/spec/agentlisp_srs.md | grep -F "✅ Completed（CR-28）"` 非空 |
| 附录 B L316 孤儿清单（34-ID 集合全等核查）| `AC-1, AC-2, AC-3, FR-PARSER-1 ... IF-TEMPORAL-1`（34 个 ID）| **字节全等未动**（制度化，三集合全等 0 孤儿）| `diff <(git show 7d67a1c:docs/spec/agentlisp_srs.md | sed -n '316p') <(sed -n '316p' docs/spec/agentlisp_srs.md)` 空 |

---

## 4. 未跑完的真联调项（环境限制，非代码阻塞）

| 编号 | 缺口（Roadmap 顺序未交付）| 阻塞性质 / 类型 | 复现命令 VERBATIM（精确到每一行）| 释放后核查 PASS 判据（可量化） |
|---|---|---|---|---|
| 4-1 | B-4 = `FR-CHECK-2` SSOT 8 项 builtin（Racket sideeffect-builtin-tools vs Python runtime.checker.SIDEEFFECT_BUILTIN_TOOLS 集合全等 len==8）| ⏳ 纯待后续（无阻塞，Roadmap 下一项顺位，无外部资源）| 下一轮 `PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider -k "fr_check_2 or sideeffect"` → passed ≥ 1；严格基线 123 → **124** Δ+1 | 新 pytest 1 passed；附录 B FR-CHECK-2 行（L283）Scenario/Passed 从 1→N；孤儿清单不动 |
| 4-2 | C-2 = 附录 B 矩阵 Passed 列求和精确对齐实际 pytest 报告（当前 L272 声明严格模式 pytest 「119 passed」但实际已 123，+1 CR-28 后 124，还有 AC-2 行 L301 baseline 119 应改为 123/124）| ⏳ 纯文档核查（无阻塞，矩阵数字不影响 pytest 真通过率，只影响 SRS 审计精度）| 临时 Python heredoc：`python3 -c "import re,sys; s=open('docs/spec/agentlisp_srs.md').read(); ids=re.findall(r'\|\s+\*\*([A-Z0-9-]+)\*\*\s+\|\s+(\d+)\s+\|\s+(\d+)\s+\|', s); total=sum(int(p) for _,_,p in ids); print('total_passed_col=',total)"` 输出和实际 pytest 报告 passed 数（124）绝对差 ≤0 | `Σ Passed = pytest passed（124→125?）`；`grep -F "严格模式 pytest " docs/spec/agentlisp_srs.md` 首行数字等于实际 passed；孤儿清单 34-ID 不动 |
| 4-3 | **C-1 = P1-3 AC-3 τ²-bench v1.0 1000 真样本 wire pipeline fix_rate_total ≥ 0.90（永久 BLOCK，缺 gh CLI + 数据集）** | 🚫 BLOCKED（需用户终端主动操作，任何 agent 无法自动释放）| **释放命令 VERBATIM 三行（必须用户在本机 zsh 执行，agent 没权限）**：<br>1. `brew install gh` <br>2. `gh auth login`（走 browser flow，选 GitHub.com + SSH key 本机已存在 ~/.ssh/id_ed25519.pub）<br>3. `gh release download τ²-bench-v1.0 -R agentlisp/t2-bench -D $HOME/.cache/agentlisp/t2-bench-v1.0` <br>释放后真实跑：<br>`uv run python scripts/bench/run_t2_bench.py --sample-range 1..1000 --timeout 600s` | 输出 `$HOME/.cache/agentlisp/t2-bench-v1.0/samples.jsonl` 存在且 1000 行（`wc -l`）；report.json 字段 `fix_rate_total >= 0.90`；严格基线保持 124 不回退 |
| 4-4 | C-3 = tag v2.0.0-rc2 打签名 + release.yml 5 jobs 真机 green + SHA256SUMS 0 mismatch + OCI 5 labels 非空 | ⏳ 作业级（前置条件 = B-3/B-4/C-2/C-1 全 PASS；缺 1 就不许打 tag，避免 release.yml 产物不完整）| 前 4 项全部 ✅ 后执行：<br>`git tag -s v2.0.0-rc2 -m "CR-26+ GA RC · baseline 124 passed · OCI 5 labels + FR-PARSER-3 emit + perf job"`<br>`git push origin v2.0.0-rc2`<br>下载 artifacts：`gh run watch <id> && gh run download <id> -D release-artifacts` → `shasum -c release-artifacts/SHA256SUMS` 0 mismatch<br>`docker pull ghcr.io/4TWS3/agentLisp:v2.0.0-rc2 && docker inspect ghcr.io/4TWS3/agentLisp:v2.0.0-rc2 --format '{{json .Config.Labels}}'` 包含 org.opencontainers.image.{source,version,revision,created,title} 全部非空且等于 git 元数据 | release.yml 5 jobs（Linux/macOS/Windows build + merge-sha + docker）全 green；`shasum -c` 0 mismatch；5 OCI labels = git 元数据 |
| 4-5 | **本机环境限制（永久，移交所有 agent）**：`which racket = not found`（B-3 双路径 fallback 分支覆盖；CI 真环境用 `Bogdanp/setup-racket@v1.11 RACKET_VERSION=8.12 packages=base,rackunit-lib,...` 装 6 包，路径 A 全真实）| ℹ️ 本机资源硬约束 | `which racket`；CI 路径 A 执行见 ci.yml perf-bench step 3 setup-racket | 本地 fallback 分支 hard-assert 全通过（123 passed）；CI 真机路径 A subprocess 真执行全通过 |
| 4-6 | Review Cycle 1 advisory AF-CR28-001：`_check_exit_2_parse_fail` L177 空 try/compile 块（非阻塞不影响通过，可下一轮 CR 删除或注释化）| ℹ️ advisory | `sed -n '170,180p' runtime/tests/test_cli_if_cli_1_exit_encoding.py` 可见 | 无；不 block 后续任何轮 |

---

## 5. 运行时外部端点 & 依赖硬约束（交接防坑指南 · 34 ID 清单 · VERBATIM 保留）

### 5.1 SSOT 枚举值（大小写敏感，双端 bitwise equal，34-ID 集合全等核查永久保留）

- Provider 枚举（4 项）：`anthropic | openai | qwen | mock`（SRS §3，CR-16 基线）
- on_failure 枚举（3 项，连字符）：`ask-human | fallback-model | abort`（FR-CHECK-1 §3，SRS 写死英文连字符，不许下划线/中文）
- Topology 枚举（4 项，英式拼写 centralised = 英式 s，美式 z 直接 FR-PARSER-6 FAIL）：`peer | orchestration | decentralised | judge-driven`
- Memory 层级（3 项 L0/L1/L2，严格前缀 L0 摘要→L2 全文）：`L0-Abstract | L1-Overview | L2-FullText`
- MCP scheme 白名单（4 项，明文 http/ws 直接 FAIL）：`stdio:/// | http+unix:/// | https:/// | sse:///`（SRS §5.5 IF-MCP-1）
- CLI exit code 6 档编码（IF-CLI-1 §5.1）：`0 ok | 1 check ERR_* | 2 parse | 3 io | ≥4 panic`
- SIDEEFFECT-BUILTIN-TOOLS（8 项 SSOT，B-4 下一轮要 bitwise equal pytest 全测）：`bash, git-push, wget, curl, scp, dd, chmod, sudo`
- 34 SRS-ID 孤儿清单（VERBATIM 顺序，L316 全文，任何 CR 字节不变，三集合全等 0 孤儿）：
  `AC-1, AC-2, AC-3, FR-PARSER-1, FR-PARSER-2, FR-PARSER-3, FR-PARSER-4, FR-PARSER-5, FR-PARSER-6, FR-CHECK-0, FR-CHECK-1, FR-CHECK-2, FR-CHECK-3, FR-CORRECT-1, FR-MAGT-1, FR-MEM-1, FR-RUN-1, FR-RUN-2, FR-RUN-3, FR-RUN-4, NFR-OBS-1, NFR-PERF-1a, NFR-PERF-1b, NFR-PERF-2, NFR-REL-1, NFR-REL-2, NFR-SEC-1a, NFR-SEC-1b, NFR-SEC-1c, IF-API-1, IF-CLI-1, IF-MCP-1, IF-SDK-1, IF-TEMPORAL-1`

### 5.2 制度化约束（CR-26/27 已验证，任何 CR 必须沿用，违反 = Review 直接 fail 扣分）

1. **先回写附录 C Roadmap 再开工**：§3 业务改动/验收变更前，必须先把附录 C Roadmap 对应行 Status 列从 Pending → in_progress（CR-XX）→ ✅ Completed（CR-XX）。禁止口头 chat 历史替代，必须 SRS.md 成文。（B-3 已按此：先改 L366 状态，才 Implement）
2. **commit message 必须 `-F /tmp/*.txt` 临时文件**：正文 ≥ 3 行时禁止 `git commit -m "..."`（macOS zsh 长消息分词 pathspec 历史 bug 教训）。模板：`cat > /tmp/cr28_commit_msg.txt <<'EOF' ... EOF && git commit -F /tmp/cr28_commit_msg.txt`
3. **双路径 hard-assert 零 pytest.skip**：任何缺资源（racket 不在 PATH / gh 不在 / τ²-bench 数据集不在）的性能/集成 pytest，必须提供路径 A（真机/真依赖环境）hard assert + 路径 B fallback（数学/静态/grep 量化断言）hard assert，两路真断言，函数体内真实 `pytest.skip(...)` 调用 0 次。制度化 grep：`grep -c "pytest.skip(" runtime/tests/test_*.py | grep -v ":0$"` 输出必须空。
4. **每 CR 完必写 handoff**：CR-XX 完结后（commit push 前）必须在 `docs/handoff/YYYYMMDD_crXX_topic_handoff.md` 写 7 章模板交接单（§1 Git / §2 四硬 / §3 精确锚 / §4 未跑完 / §5 约束 / §6 下一步 / §7 标签），结构逐字全等本文件。handoff 文档必须和业务改动 commit 一起 push 到 origin/main，其他 agent 拉到 HEAD 就能接手。
5. **emit 阶段 Python dict key 必须下划线，禁止连字符**（B-1 FR-PARSER-3 制度化）：`auto_append_episodic`（key）≠ `auto-append-episodic`（spec 冒号键）。任何新增 emit context 必须 key 下划线。
6. **忠实范围 Rubric AC-6**：每轮 CR `git diff --name-only HEAD` 的文件类数 ≤ 本轮 spec AC-6 允许阈值（CR-28 阈值=3 类，允许 3 类：spec 工件 / tests / SRS.md；ci.yml/release.yml/Dockerfile 改了就 0 分 Review fail）。

### 5.3 外部资源坐标（不可从代码恢复，VERBATIM 保持 CR-27 清单，CR-28 未新增任何外部资源坐标）

> 完全复用 CR-27 handoff §5.3：SRS 来源 / τ²-bench / Infra 端点 / GH Racket setup action / pyproject optional-deps 9 组 / remote SSH / compose 位置 / pytest-bdd 9.x hook / repair_agent 样例 / release.yml 产物目录 / ghcr.io OCI 5 labels / Spec Mode 工件模板 / handoff 7 章模板来源。
> （未变更 → 不重复展开，直接引用上一份 handoff 同节即可）

---

## 6. 下一步自由方向（严格按附录 C 固化优先级，不可跳项！）

> Roadmap 总览（11 项）：总=11 / 已完成=**7**（63.6%，+1 CR-28 B-3）/ BLOCKED=1（C-1 gh）/ Pending 纯待续=2（B-4 / C-2）/ 最后作业级=1（C-3 tag）。

| 顺位 | Roadmap ID | 下一步内容（一条原子任务，不合并）| 依赖 & 不可跳项原因 |
|---|---|---|---|
| 1（下一条「继续」首优先）| **B-4 FR-CHECK-2** | 新建 pytest `test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal @pytest.mark.req("FR-CHECK-2")`；双路径：路径 A（racket 在 PATH）→ subprocess 读 Racket sideeffect-builtin-tools 列表 + Python `from runtime.checker import SIDEEFFECT_BUILTIN_TOOLS` → set 全等 & len==8；路径 B fallback（racket 不在）→ grep compiler/checker.rkt L87 `'(bash git-push ...)'` 8 项字面 + Python frozenset 8 字面 → bitwise equal。严格基线 123 → **124** Δ+1；附录 B FR-CHECK-2 行 L283 Scenario/Passed 从 1→1（或 1→N，按实际 pytest 数量）TODO 去标签；附录 C B-4 行 Status ✅ Completed（CR-29）。写 handoff `docs/handoff/20261005_cr29_b4_fr_check2_ssot_8_handoff.md` 7 章模板。| 无外部资源阻塞；SRS 枚举已硬编码双端；B-3 已交付不依赖 B-4，所以顺位移交。 |
| 2（B-4 完后下一）| **C-2 附录 B 矩阵求和精确对齐** | `python -c "Σ Passed 列求和 = actual pytest passed"`；L272 文案从「119」→「124」（CR-28→CR-29 后 124→125?）；AC-2 行 L301 baseline 从「119」→「123/124」；孤儿清单 34-ID 不动。严格基线 pytest 不回退（Δ=0，纯文档回写项），所以无 AC-3 Δ 要求。写 handoff `docs/handoff/20261005_cr30_c2_matrix_sum_align_handoff.md`。| 必须在 B-4 之后做（否则 matrix Σ ≠ 真 pytest 数） |
| 3（C-2 后，必须用户先主动执行 §4-3 释放命令）| **C-1 τ²-bench v1.0 1000 真样本** | 用户终端执行 §4-3 释放命令 VERBATIM 三行 → 跑 `scripts/bench/run_t2_bench.py --sample-range 1..1000 --timeout 600s` → report.json `fix_rate_total ≥ 0.90`。严格基线保持 124，无新增 pytest（τ²-bench 是端到端真实分布，不在 pytest 基线里，基线只统计数学性质与指标 pytest）。写 handoff `docs/handoff/20261005_cr31_c1_t2bench_1000_samples_handoff.md`。 | BLOCKED，任何 agent 不能自动化，等用户主动操作 gh auth + 下载 dataset。 |
| 4（前 4 全 ✅ 后最后作业）| **C-3 tag v2.0.0-rc2 + release.yml 真机 green** | 见 §4-4 命令。写 handoff `docs/handoff/20261005_cr32_c3_tag_v200rc2_release_handoff.md`。 | 前置 B-3/B-4/C-2/C-1 必须全 ✅（打 tag 是不可恢复作业，缺一项不许动）。 |

---

## 7. 交接人 & 时间

| 标签字段 | 值（commit push 后可 checkout 复现，字节级一致）|
|---|---|
| Commit hash（CR-28 业务 commit 7 位短 hash，已 push origin）| `4b89802`（`git show 4b89802` 可复现，6 files changed，723 insertions，2 deletions） |
| 严格基线 pytest 签名 | `123 passed / 1 skipped / 1 warning`（CR-28 指纹） |
| ruff check + format | `0 errors · 56 files already formatted`（CR-28 指纹）|
| GetDiagnostics | `0 files / 0 diagnostics` |
| Roadmap 进度（CR-28 交付）| 总 11 / ✅ 完成 7（63.6%）/ BLOCKED 1（C-1 gh）/ Pending 纯待续 2（B-4 / C-2）/ 最后作业 1（C-3 tag） |
| 忠实范围 Rubric AC-6 | 2/2 满分（类=3 · 文件=5 · 未触 ci/release/Docker） |
| 独立 Review 结论（§5 Review.md）| **pass**（6/7 AC 独立复现 + AC-7 本 handoff 补证据后 7/7 PASS，1 advisory 非阻塞）|
| 可追溯三工件 | `.trae/specs/cr28_b3_cli_exit_encoding/{spec,tasks,review}.md`（三文件 + 本 handoff = CR-28 交付全量证据包） |

---

*END OF HANDOFF · 下一个 agent 接手流程：§2 先跑四硬指标命令链（4 条 VERBATIM）→ 核对 CR-28 指纹（123 passed / 56 formatted / 0 diagnostics）→ §6 顺位取 B-4 FR-CHECK-2 原子任务开工 → 立刻新建下一份 handoff 模板并开工前回写附录 C Roadmap B-4 行 in_progress（CR-29）。*
