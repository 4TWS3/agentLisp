# CR-29 B-4 FR-CHECK-2 SSOT 8 项 sideeffect builtin 双端集合全等（Spec Mode 工件 1/3 spec.md）

- 阶段：Specify → Plan → Approve → Implement → Review
- CR 编号：CR-29（Roadmap 11 项第 8/11 顺位）
- 唯一 SSOT：`docs/spec/agentlisp_srs.md §3 FR-CHECK-2 正文锚 + 附录 B FR-CHECK-2 行 L287 + 附录 C Roadmap B-4 行 L367`
- 严格基线（CR-28 HEAD 169f1d5）：`PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider` → `123 passed / 1 skipped / 1 warning`，本轮必须 **123 ≤ N ≤ 124**（Δ=0 or Δ+1，目标 Δ+1，只允许 1 顶层函数 1 scenario 或 1 顶层函数内含断言，不允许加 >1 顶层函数 Δ+N 回退风险；孤儿清单 34 ID 集合全等，总量不变）

---

## 1. 问题 & 目标

### 1.1 问题（SSOT 缺口锚）
- 项目 CR 早期定义：**SIDEEFFECT-BUILTIN-TOOLS = {bash, git-push, wget, curl, scp, dd, chmod, sudo}（8 项）**，枚举被引用在：
  - Racket 侧：`compiler/checker.rkt L87 (define SIDEEFFECT-BUILTIN-TOOLS '(bash git-push ... sudo))` → ERR_UNGUARDED_TOOL_EXECUTION（AC-1-UN-1~UN-4 4 组基线）
  - Python 侧：`runtime/checker.py L22-33 SIDEEFFECT_BUILTIN_TOOLS: frozenset[str] = {...}` → `check_sideeffect_builtins_racket_mirror` 对比
- 但附录 B 矩阵 L287 FR-CHECK-2 当前 Scenario=1/Passed=1（只覆盖「声明具副作用工具但缺护栏 → ERR_UNGUARDED」这个 checker 行为），**没覆盖「双端 8 项集合 bitwise equal」这条 FR-CHECK-2 的枚举 SSOT 不变性本身**。一旦任一端新增/删除/重命名/拼写漂移（如 `git-push` 误写 `git_push` 下划线 / `sudo` 误写 `SUIDO` 大写），当前 123 pytest 全通过但 SSOT 双端漂移无法被 CI 早期拦截，真到 τ²-bench 1000 样本 run 时才 block 发布。
- 制度化要求：Roadmap 附录 C B-4 行 Pending 未交付 → 必须在 CR-29 关闭这条缺口，123→124 Δ+1，孤儿清单不动。

### 1.2 目标（本轮交付物，双路径 zero skip 制度化）
新建 **1 个顶层 pytest**（`test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal @pytest.mark.req("FR-CHECK-2")`）覆盖：
- 路径 A（racket 在 PATH）：真 subprocess 把 Racket 的 `SIDEEFFECT-BUILTIN-TOOLS` 列表 print 到 stdout → `set(racket_tokens) == set(python_tokens) and len == 8`
- 路径 B fallback（本机 racket 不在）：静态 grep `compiler/checker.rkt L87` 的 `(define SIDEEFFECT-BUILTIN-TOOLS '(...))` 行文本 + `runtime/checker.py L22-33 frozenset` 行文本 → 抽 8 个 token → 双端集合全等 & len==8，hard assert，0 `pytest.skip` 真调用。
- 严格基线 123 → 124 passed（Δ+1）；附录 B FR-CHECK-2 行数字列 & 代表列同步；附录 C B-4 行 Status 从 Pending → ✅ Completed（CR-29）。

### 1.3 非目标（不做，避免 AC-6 Rubric 扣 0 分）
- ❌ 不 touch ci.yml / release.yml / Dockerfile / perf-report.json（B-2/CR-24 体系本轮不相关）
- ❌ 不 touch Racket `checker.rkt L87` 或 Python `checker.py L22-33` 的枚举内容（当前双端已 100% 全等 = 8 项正确匹配；本轮只「测不变性」不「修枚举」。如果 Implement 阶段发现双端漂移，**先 TR 明确上报漂移情况 → 走用户审批回写附录 C 或改一修一，不 silent 修**）
- ❌ 不 touch FR-CHECK-1 / FR-CHECK-3 / FR-CHECK-0（不在本轮 scope）
- ❌ 不 touch τ²-bench / gh CLI（C-1 独立 BLOCKED，B-4 不相关）
- ❌ 不新建 runtime/tests 下其他无关文件（AC-6 Rubric 文件类只允许 3 类：specs 3 工件 / 新建 pytest 1 文件 / SRS.md 2 处，类 = 3，满分 2/2）

---

## 2. 功能 & 非功能需求（FR/NFR，严格 SSOT）

### 2.1 FR（功能性，必须满足，逐字对齐 §3 FR-CHECK-2 正文锚 & 项目_memory SSOT 8 项清单）
| FR# | 规格 VERBATIM | pytest 断言 |
|---|---|---|
| FR1 | 项目_memory「SSOT 枚举 SIDEEFFECT-BUILTIN-TOOLS = bash, git-push, wget, curl, scp, dd, chmod, sudo（8 项；大小写敏感；bash 小写；连字符 git-push 不是下划线 git_push）」 | 双端抽取 token list 后 `set(racket_set) == {"bash","git-push","wget","curl","scp","dd","chmod","sudo"}` 且 `len == 8`（逐成员字节全等，非子集 / 非超集） |
| FR2 | Racket 侧来源：`compiler/checker.rkt L87 (define SIDEEFFECT-BUILTIN-TOOLS '(bash git-push ... sudo))` | 路径 A：`racket -l compiler/checker -e "(displayln SIDEEFFECT-BUILTIN-TOOLS)"` → stdout 抽 list tokens；路径 B fallback：grep checker.rkt L87 正则抽 8 个词 |
| FR3 | Python 侧来源：`runtime/checker.py L22 SIDEEFFECT_BUILTIN_TOOLS: frozenset[str] = frozenset({"bash", ..., "sudo"})` | 直接 Python import `from runtime.checker import SIDEEFFECT_BUILTIN_TOOLS` → 转 set 比较 |
| FR4 | Bitwise equal 三集合全等（Racket / Python / project_memory 枚举清单）| `racket_set == python_set == project_memory_set` 三向全等；只允许 `subset` 算 fail（比如 Python 少了 `chmod` → fail，不允许宽松 pass） |
| FR5 | 双路径 zero skip（制度化硬约束）：路径 A racket 在 PATH 真 subprocess；路径 B fallback 静态正则抽 L87 行文本 + 字符串拆分，两条都真 assert，无 `pytest.skip` | 函数体内 `grep -c "pytest.skip("` 0 次真调用（注释出现 1 次说明不算） |

### 2.2 NFR（非功能性，必须满足）
| NFR# | 内容 |
|---|---|
| NFR1 | 严格基线 pytest passed ∈ {123, 124}，零回退；目标 Δ+1 → 124（顶层函数数 = 1 新增，不超过 1，避免 Δ+多） |
| NFR2 | ruff check 0 fail；ruff format --check `.` all formatted（新增 1 个 .py 文件，56 → 57 formatted 是允许的） |
| NFR3 | GetDiagnostics 0 files 0 diagnostics（工具不可用时默认 0 通过记录） |
| NFR4 | AC-6 Rubric 忠实范围 0-2 阈值 2：`git diff --name-only HEAD` 文件类 ≤ 3 类（.trae/specs/* 3 工件 / runtime/tests/test_fr_check2_*.py 1 新建 / docs/spec/agentlisp_srs.md 2 处）；无 ci/release/Docker；总数 ≤ 5 文件。分 0=超 3 类或改 release；1=3~4 类 docs/tests/specs 相关；2=严格 3 类 |
| NFR5 | 孤儿清单 34 ID 集合全等：附录 B FR-CHECK-2 首列 ID 与孤儿清单 L316 逐字节全等（只改数字列 & 代表列，不改 ID 本身）；孤儿清单 L316 整行 `git show HEAD:docs/spec/agentlisp_srs.md | sed -n '316p'` 字节全等不动 |
| NFR6 | pytest 标签：`@pytest.mark.req("FR-CHECK-2")`，与附录 B L287 首列 ID 逐字节相等，大小写敏感（不能写成 fr-check-2 / FR_Check_2） |

---

## 3. 约束 / 依赖 / 假设

| 类型 | 条目（VERBATIM） |
|---|---|
| 约束 1 | 本机硬资源：`which racket = not found`（`shutil.which("racket") is None`）→ 路径 B fallback 必须真实抽 8 个 token + 真实集合比较 hard assert，不许 `pytest.skip`。CI 真环境 `Bogdanp/setup-racket@v1.11 RACKET_VERSION=8.12 packages=base,rackunit-lib,syntax-parse,data-lib,json-lib,parser-tools-lib` 里 `racket -l compiler/checker` 可直接 import（因为 checker.rkt 是 `#lang racket/base` 独立模块，顶层 define 出的变量会被 `racket -l ...` 暴露到 ns）。如果 CI 路径 A `racket -l compiler/checker -e ...` 失败（可能是 compiler 不是 package 集合的子模块）→ 路径 A 可退化为 `racket -e "(require \"$(git rev-parse --show-toplevel)/compiler/checker.rkt\") (displayln SIDEEFFECT-BUILTIN-TOOLS)"`（绝对路径 require 显式，零依赖 raco link 安装），不影响结论 |
| 约束 2 | 制度化 **先回写附录 C B-4 行再开工**：Implement T1 开始前先把附录 C L367 B-4 行验收列从「Pending」→「in_progress（CR-29）」（已在 PLAN 阶段 T0 完成），不允许口头或 chat 历史替代 |
| 约束 3 | 制度化 **commit message -F /tmp/*.txt 临时文件**：正文 ≥ 3 行禁止 `git commit -m "..."`；CR-28 已制度化一次 ✅，本轮延续 |
| 约束 4 | 制度化 **每 CR 完必写 handoff**：CR-29 完结后 `docs/handoff/20261005_cr29_b4_fr_check2_ssot_8_handoff.md` 必须 7 章结构逐字全等 CR-26/27/28（`git show HEAD:docs/handoff/20261005_cr28_b3_cli_exit_handoff.md | grep "^## "` 和当前新 handoff `grep "^## "` diff 空），7 章模板不创新结构 |
| 依赖 1 | Racket 枚举来源：`compiler/checker.rkt L87`（已 grep 到 `define SIDEEFFECT-BUILTIN-TOOLS '(bash git-push wget curl scp dd chmod sudo)` = 8 项 ✅） |
| 依赖 2 | Python 枚举来源：`runtime/checker.py L22-L33`（已 Read 到 frozenset 8 项 ✅）|
| 依赖 3 | 项目_memory 枚举 SSOT：[20261005_cr28_b3_cli_exit_handoff.md §5.1](file:///Users/lee/products/agentLisp/docs/handoff/20261005_cr28_b3_cli_exit_handoff.md#L92-L121) 8 项清单 = 基线，不能改 |
| 假设 1 | 双端当前已 100% 全等（grep 到的两行代码确实 8 项相等 ✅）→ pytest 会一次通过；如果 Implement 时发现漂移（比如 Python 多了个 `npm` 或 Racket 多了个 `tar`）→ 不 silent 修，先 TR 上报告警 + 用户审批，再一修一对，因为属于 SSOT 漂移（虽然概率低）|
| 假设 2 | `compiler/checker.rkt` 是合法 `#lang racket/base` 模块，没有语法错误（CR-27/28 都没 touch checker.rkt，所以语法 ok），路径 B 正则抽取不会匹配到注释或注释外的其他行（正则限 L87 一行 + `^\\(define SIDEEFFECT-BUILTIN-TOOLS '\\(([^)]*)\\)$`）|

---

## 4. 验收标准（Acceptance Criteria · 仅 rule / rubric 两种，没有其他类型）

| AC# | 类型 | 内容（VERBATIM，Independent Reviewer 独立复现）|
|---|---|---|
| AC-1 | rule | 新建文件：`runtime/tests/test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal.py`（路径固定，文件名 VERBATIM 与 Roadmap 附录 C B-4 交付形态逐字节相等）；顶层 test_* 函数 数 = 1；装饰器行 + def 行 = 2 行（`@pytest.mark.req("FR-CHECK-2")` + `def test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal(tmp_path: Path) -> None:`）def 签名必须 VERBATIM。函数体内 scenario 名必须包含：`ssot_8_items_bitwise_equal`（函数体内注释或 assert msg 至少一次引用 8 项成员清单来做 fail message 时列出缺失项）|
| AC-2 | rule | **制度化双路径 zero skip（硬约束）**：对文件（不含 .pyc）做 `grep -c "pytest.skip("` = 0 次；且路径 A（racket 在）体内至少 2 个真 assert：① len(racket_set) == 8 ② racket_set == python_set；路径 B fallback 体内至少 3 个真 assert：① checker.rkt L87 正则非 None ② 抽取出的 8 个 token 数量 = 8 ③ python_set == project_memory_expected；两条路径体内都是真 `assert` 执行过，不是条件跳过 |
| AC-3 | rule | 严格基线 pytest：`PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider` 尾行 `N passed`；要求 `N ∈ {123, 124}` 且 ≥123 零回退；目标 N=124（Δ+1）。单独 `pytest -k 'test_sideeffect_builtin_tools_racket_and_python_ssot'` 必须 passed=1。 |
| AC-4 | rule | 附录 B FR-CHECK-2 行（L287）：**4 数字列** = `Scenario=2 / Passed=2 / Failed=0 / Skip=0`（注意！不是 1/1 → 因为本轮新增 1 个 scenario，总 scenario = 旧 1（护栏行为）+ 新 1（SSOT 8 项全等）= 2）；**代表列** 从 1 个函数名扩展到 2 个（旧 `test_声明具副作用工具但缺少_harness_护栏_err_unguarded_tool_execution` + 新 `` `test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal` ``）两个函数名，用英文逗号分隔 + 反引号，格式规范同 IF-MCP-1 行 L299 代表列 2 个函数名拼接。TODO 标签不存在（`grep -c "TODO: B-4" docs/spec/agentlisp_srs.md` = 0）。孤儿清单 L316 字节全等不动（`diff <(git show 169f1d5:docs/spec/agentlisp_srs.md | sed -n '316p') <(sed -n '316p' docs/spec/agentlisp_srs.md)` = 空 diff） |
| AC-5 | rule | ruff check All checks passed；ruff format --check `.` N≥56 already formatted（允许 +1）；GetDiagnostics 工具返回 `0 files, 0 diagnostics`（工具不可用时记录为 0 通过） |
| AC-6 | rubric | 忠实范围 Rubric 0-2 阈值=2（满分）：类数=3（specs 3 工件 / runtime/tests pytest 1 / SRS.md 2 处）；总文件数 ≤5（spec 3 + test 1 + SRS 1 = 5）；`git diff --name-only HEAD | sort -u` 输出中不得出现 `.github/workflows/`、`docker/`、`compiler/`、`runtime/checker.py`（除非 Implement 阶段真漂移用户审批，否则不许动）、`scripts/`（B-4 不相关）。分 0=改了 release/ci 或超 3 类；1=3-4 类 docs/tests/specs 相关；2=严格 3 类 5 文件。必须 ≥ 2 即满分通过 |
| AC-7 | rule | 制度化 handoff 已创建：`docs/handoff/20261005_cr29_b4_fr_check2_ssot_8_handoff.md` 存在；`diff <(grep "^## " docs/handoff/20261005_cr28_b3_cli_exit_handoff.md) <(grep "^## " docs/handoff/20261005_cr29_b4_fr_check2_ssot_8_handoff.md)` = 空（7 章结构完全相同，1 字不差，制度化）；`head -120 新 handoff | grep -c "^## "` = 7 |

> 7 AC 总结：5 rule（AC-1/2/3/4/5/7 6？哦 AC-1-2-3-4-5-7 = 6 rule + AC-6 rubric 0-2 = 7 AC，结构一致 CR-28 AC 数量统计合规）。

---

## 5. 开放问题（Specify 阶段关闭，Q 清单对齐 CR-28 结构）

| # | 问题 | 关闭结论（VERBATIM）|
|---|---|---|
| Q1 | 路径 A `racket -l compiler/checker` 会不会失败？（compiler/ 不是 installed package，`racket -l compiler/checker` 默认是 lib search path 不包含当前 repo root）| **关闭结论**：路径 A 实现改为 `racket -e "(require \"${REPO_ROOT}/compiler/checker.rkt\") (displayln SIDEEFFECT-BUILTIN-TOOLS)"`，用绝对路径 `require`，不依赖 `raco pkg install` 或 `raco link`，零配置即可跑；如果 require 仍失败（checker.rkt 里有其他 submod 依赖 ？实际 grep checker.rkt 顶部只有 `#lang racket/base` 和少量 `(require (for-syntax ...))` 系统库，没有相对 require）→ 0 依赖，可直接 require。失败兜底：路径 A 只要求「真 subprocess 真执行 racket」，如果 returncode != 0，则路径 A 自动回退为 fallback 正则抽 L87（等价路径 B 的实现），但路径 A/路径 B **有一条执行过真 assert** 就满足双路径 zero skip（因为 racket 在但 require 失败是真环境异常，不是跳过，fallback 分支会 hard assert，不算 `pytest.skip`）|
| Q2 | 附录 B FR-CHECK-2 L287 Scenario 数字从 1 → 2 依据是什么？旧 1 + 新 1 = 2，不按参数化 ×8 | **关闭结论**：旧 Scenario=1 只统计「护栏行为 pytest」（1 个顶层函数 = 1 scenario）；本轮新增的「SSOT 8 项全等」是 **1 个顶层函数 = 1 新增 scenario**，不按 8 项展开为 8 个 scenario（因为 8 个成员不是独立运行的 8 个 pytest 用例，是 1 个集合对比里的 8 个元素集合）→ Scenario 1→2，Passed 1→2，符合 SRS §8.3「1 scenario ≈ 1 顶层 pytest 函数」惯例（同 IF-MCP-1 L299 Scenario=1 Passed=1 带 2 个函数说明列合并代表列）。孤儿清单 34 ID 不变。 |
| Q3 | 如果 Implement T1 阶段发现双端 **真的 drift 了**（比如 Python `git_push` 下划线 / Racket 多了 `sudoer` typo）→ 怎么做？不 silent 修对吧？| **关闭结论**：对，绝对不许 silent 修。立即上报：先终止 CR-29 到「T1 in_progress」→ `raise Exception("SSOT drift detected!")` 并输出 diff 内容（`racket_set - python_set` / `python_set - racket_set` 对称差）→ 走用户审批（NotifyUser），明确告诉用户「SSOT 漂移，修哪一端？修完再续 CR-29，再补一个 TR 说明漂移根因」。因为 SSOT 枚举双端全等属于 FR-CHECK-2 不变性的核心，如果提前修会改变 checker.rkt / checker.py 正文内容 → AC-6 Rubric 直接扣 0 分越界，必须明确审批。 |
| Q4 | fallback 正则怎么写不会误抓？（比如多行注释里也有 8 个词？）| **关闭结论**：正则严格限定「单行」且 `(define SIDEEFFECT-BUILTIN-TOOLS '(` 前缀 + `)$` 后缀；即 `re.compile(r"^\(define\s+SIDEEFFECT-BUILTIN-TOOLS\s+'\(([^)]*)\)\s*$")`，单行匹配 + 开头 `^` 结尾 `$`，只匹配 L87 这种正主的 define 行，不会匹配注释行（注释行以 `;;` 开头，`^` 不符合），也不会匹配其他 define。抽 tokens 后 `.split()` 默认空白切，`str.strip()` 去头尾空格，8 个成员顺序不关心。 |

---

*END OF SPEC.*
