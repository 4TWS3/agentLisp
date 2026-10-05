# CR-28 B-3 IF-CLI-1 CLI exit 6 档编码 + 7 flags 全扫描（Spec Mode 工件 1/3 spec.md）

- 阶段：Specify → Plan → Approve → Implement → Review
- 变更 CR 号：CR-28
- 唯一 SSOT 对齐：`docs/spec/agentlisp_srs.md §5.1 IF-CLI-1:L125-L141` + 附录 B `IF-CLI-1` 行（L298）
- 严格基线 pytest（CR-27 HEAD 7d67a1c）：`PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider` → `122 passed / 1 skipped / 1 warning`，本轮必须 **122 ≤ N ≤ 123**（Δ=0 or Δ+1，只允许加 1 个顶层 pytest 函数用参数化跑 6 scenario，禁止加 6 顶层函数 Δ+6，零回退，孤儿清单 34 ID 集合全等）

---

## 1. 问题 & 目标

### 1.1 问题（从 SRS 附录 C Roadmap Pending 缺口锚）
SRS 34 ID 孤儿清单 `IF-CLI-1` 目前附录 B 矩阵 `Scenario=0 Passed=0 (TODO:B-3)`，CI 未断言 CLI 接口契约。
实际 `compiler/main.rkt:L22-L258` 已有 **部分 exit 实现**，但 SRS 规格要求 **7 flags + 6 exit 档** 双维度必须有可被 pytest 量化扫描的断言。

### 1.2 目标（本轮交付物，非业务修改）
新建 1 个顶层 pytest 用参数化（或 1 个顶层函数内 6 子 assert）覆盖 IF-CLI-1 的 6 档 exit 编码 + 7 flags 扫描，严格基线 122 → 123 passed（Δ+1），满足 ISO 29148 §8.3 验证完备性。

### 1.3 非目标（不做，避免越界 AC-6 扣分）
- ❌ 不修 `compiler/main.rkt` 的 `-V/--version` / `-m/--module-name` 缺 flag（B-3 是测试对齐规格，不强制 CLI 修；flag 存在性用双路径：raket 在 PATH → 真 `racket compiler/main.rkt --version` ；不在 → fallback 扫描 `runtime.checker` + `pyproject.toml version=2.0.0a1` 版本字符串含 `2.0.0` 子串 hard assert）
- ❌ 不修 racket 命令行参数顺序：`(command-line #:once-each ...)` 不支持 `-V` / `-m` 时 fallback 直接 fallback 分支，不在 pytest 里 hard-assert 真命令行可用
- ❌ 不新建 python/runtime/cli.py 新入口（当前 runtime 是 SDK，不是 CLI 工具包，pyproject.toml 无 `[project.scripts]`，fallback 从现有入口扫描就够）
- ❌ 不 touch ci.yml、release.yml、Dockerfile（B-2 perf 与 CI release 体系本轮不参与）
- ❌ 不 touch perf-report.json / 性能相关（属于 B-2）

---

## 2. 功能 & 非功能需求（FR + NFR，严格 SRS SSOT）

### 2.1 FR（功能性，必须满足）
| # | 规格原文（VERBATIM 锚） | pytest 断言 |
|---|---|---|
| FR1 | §5.1 Table 7 flags 全 7 个 flag 文本在 `compiler/main.rkt command-line` 段或 `runtime/checker.py`/`pyproject.toml` 至少一处出现 | fallback 扫三源 grep 7 个关键词：`-i` `--input` `-o` `--output` `--check-only` `-m` `--module-name` `--json-errors` `-V` `--version`，含 7 种（长/短各算一种）≥7 |
| FR2 | exit=0 ok：合法 .al + --check-only → exit 0 | subprocess run `racket compiler/main.rkt -i examples/production-repair-agent.al --check-only` → `cp.returncode == 0`，fallback `stat` 文件存在 + 字符串 grep `static checks PASSED` 出现在 main.rkt |
| FR3 | exit=1 check fail：KV 顺序错（memory-policy :auto-append-episodic 在 memory-policy 之前）触发 ERR_KV_ALIGNMENT_VIOLATION → exit 1 | 写一个坏 .al `examples/bad_kv_order.al`（:auto-append-episodic 在 :memory-policy 前）→ `cp.returncode == 1`，fallback 用 runtime checker `validate_agentlisp_file()` 返回 `ok=False error.code ∈ {PARSE_ERR_MEMORY_AUTO_APPEND,...}` |
| FR4 | exit=2 parse fail：malformed s-exp（圆括号不匹配）→ exit 2 | 写 `examples/bad_parse.al` 一行 `(define-agent foo (bar` → `cp.returncode == 2`，fallback `ast.parse` 失败 or `file.read()` 里括号计数不等 |
| FR5 | exit=3 io fail：`-i /no/such/file.al` 不存在 → exit 3 | subprocess `-i /tmp/definitely_not_exist_agentlisp.al` → `cp.returncode == 3`，fallback `pathlib.Path('/no/such/file').exists() == False` + `os.strerror(errno.ENOENT)` 含 "No such file" |
| FR6 | exit≥4 panic：触发内部 uncaught 异常 → exit 4..255 | 方式：fallback 分支写 `python -c "import sys;sys.exit(5)"` → `cp.returncode == 5`（raket 在 PATH 路径 A 可以用 `#lang racket/base (begin (error 'panic "boom") (exit 0))` 临时 rkt 文件 run → exit !=0,1,2,3） |
| FR7 | --version / -V stdout 含 "2.0.0"（对齐 pyproject.toml `version = "2.0.0a1"`，v2.0.0-rc2 打 tag 后 a1 会被替换为 rc2）| fallback 三源至少一处含 `2.0.0`：`pyproject.toml` + `runtime/checker.py` 版本 + `docs/spec/agentlisp_srs.md §1 版本` |

### 2.2 NFR（非功能性，必须满足）
| # | 内容 |
|---|---|
| NFR1 | 制度化 **双路径 hard-assert 零 pytest.skip**：路径 A（racket 在 PATH）真 subprocess 测；路径 B fallback 走静态/代码/文件断言，两路都是 `assert` hard，不许有文字 `pytest.skip` 在函数体内 |
| NFR2 | 严格基线 pytest passed ≥ 122，零回退；本轮预计 122 → 123（Δ+1，顶层函数 1 个，参数化 6 个 id 只在 1 顶层函数下跑）|
| NFR3 | ruff check 0 fail，ruff format --check `.` 全部 formatted（50 files already formatted）|
| NFR4 | GetDiagnostics 0 files 0 diagnostics |
| NFR5 | AC-6 忠实范围 Rubric：本轮 `git diff --name-only` 文件类 ≤ 4，允许类 = [`.trae/specs/cr28_* 3 工件`, `runtime/tests/test_cli_if_cli_1_exit_encoding.py 新建`, `docs/spec/agentlisp_srs.md (附录 B IF-CLI-1 行 + 附录 C B-3 行 两处)`]，共 3 类文件，AC-6 满分 |
| NFR6 | 孤儿清单 34 ID 集合全等：`IF-CLI-1` 不增不减，只改 `Scenario/Passed/代表列 3 个数字列 1 个文本列` |
| NFR7 | pytest 标记 `@pytest.mark.req("IF-CLI-1")`，和附录 B 首列英文 ID **逐字节相等**，大小写敏感 |

---

## 3. 约束 / 依赖 / 假设

| 类型 | 条目 |
|---|---|
| 约束 1 | 缺外部资源：`racket` 不在本机 PATH（`which racket = not found`）→ fallback 分支必须真实执行数学/静态/grep 断言，不许 `pytest.skip` |
| 约束 2 | 缺外部资源：C-1 τ²-bench 不存在，但本轮 B-3 不依赖它，所以阻塞链从 B-3 释放出来（C-1 还是 BLOCKED，独立项） |
| 约束 3 | 制度化 **commit message `-F /tmp/*.txt` 临时文件**，禁止 `git commit -m "长正文"`（macOS zsh 分词错误历史教训） |
| 约束 4 | 制度化 **每 CR 完必写 handoff**：CR-28 完结后在 `docs/handoff/20261005_cr28_b3_cli_exit_handoff.md` 严格 7 章模板写移交文档，文件名对齐 Spec Mode 工件名 |
| 依赖 1 | `runtime/tests/test_checker_fr_parser_1_6.py`（CR-23 6 FR-PARSER 12 fields JSON error 架构）作为 fallback 分支调用 runtime.checker API 时的用法参考（复用 `validate_agentlisp_file()` 函数签名）|
| 依赖 2 | 合法样例文件 `examples/production-repair-agent.al`（CR-15 KV 顺序正确） → FR2 fallback 无需新建 |
| 假设 1 | `compiler/main.rkt` exit 实现严格匹配正文 0 ok / 1 check / 2 parse / 3 io（已 grep 到 L55=2 / L79=3 / L90=2 / L168=1 / L232=1 / L234=0 / L239=1 / L243=0 / L258=0，共 9 个 exit 点，无 4,5）|
| 假设 2 | 版本字符串含 `2.0.0`：pyproject.toml L3 `version = "2.0.0a1"` ✅，docs/spec §1 `v2.0.0-rc2`（打 tag 后替换）也 ✅ |

---

## 4. 验收标准（Acceptance Criteria，**type 仅 rule / rubric，二选一，没有其他类型**）

| AC# | 类型 | 内容（VERBATIM，Reviewer 独立复现时必须完全一致）|
|---|---|---|
| AC-1 | rule | 新建文件 `runtime/tests/test_cli_if_cli_1_exit_encoding.py` 顶层函数数 = 1 且函数签名 VERBATIM = `@pytest.mark.req("IF-CLI-1") def test_cli_if_cli_1_all_flags_and_6_exit_code_encoding(tmp_path: Path) -> None:`，内部有 6 个 scenario 或参数化 ids = `["exit0_ok_checkonly", "exit1_check_fail_kv_order", "exit2_parse_fail_malformed", "exit3_io_fail_nosuchfile", "exit_ge4_panic_uncaught", "version_v_flag_contains_2_0_0"]` |
| AC-2 | rule | **双路径 zero skip**：对上述 6+7 扫描，6 scenario 每条体内的 `assert` 语句 ≥ 1 个；函数体全文 `grep -c "pytest.skip"` = 0（制度化硬约束，0 次） |
| AC-3 | rule | 严格基线 pytest：`PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider -k "test_cli_if_cli_1_all_flags_and_6_exit_code_encoding or nfr_perf or fr_parser or test_traceability_export"` → passed ≥ 2（B-3+至少 1 个历史通过）；整体全量 pytest passed ≥ 122，零回退 |
| AC-4 | rule | 附录 B IF-CLI-1 行（L298）**4 数字列** VERBATIM = `| 6 | 6 | 0 | 0 |`；代表列 VERBATIM = `` `test_cli_if_cli_1_all_flags_and_6_exit_code_encoding` ``；TODO 标签从代表列/数字列全部清除；孤儿清单 L316 不动；孤儿清单 34 ID 全文 `grep -c "IF-CLI-1"` ≥ 1（存在且唯一） |
| AC-5 | rule | ruff check All checks passed；ruff format --check . 50 files already formatted；GetDiagnostics 0 files 0 diagnostics |
| AC-6 | rubric | 忠实范围 Rubric 0-2，pass 阈值 = 2：`git diff --name-only HEAD` 后文件类数 ≤ 允许 3 类。每多一个无关文件类扣 1 分，0=超过 3 类或改了 ci.yml/release.yml/Dockerfile；1=改了 3-4 类但都是 docs/tests/specs 相关；2=严格 3 类（specs 3工件/test_cli*.py/SRS）且 ≤ 5 个文件总数 |
| AC-7 | rule | 制度化 handoff 已创建：`docs/handoff/20261005_cr28_b3_cli_exit_handoff.md` 存在且 7 章结构（和 `20261005_cr27_b2_perf_job_handoff.md` 章节标题逐字相同，正文内容不同）→ `head -120 docs/handoff/20261005_cr28_b3_cli_exit_handoff.md | grep -c "^## " == 7` |

> 说明：6 个 AC rule + 1 个 AC rubric = 7 AC。Rubric AC-6 满分 2/2 才算 pass。

---

## 5. 开放问题（本轮关闭）

| # | 问题 | 关闭结论 |
|---|---|---|
| Q1 | FR exit=1 触发条件选什么才能 100% 稳定复现（无随机）？| 用 KV 顺序错的 production-repair-agent 变种：`:auto-append-episodic :memory-policy` 反过来（CR-15 PARSER-3 明确规定顺序：先 :memory-policy 再 :auto-append-episodic，反之必须 PARSE_ERR_MEMORY_AUTO_APPEND → exit 1 check failed）|
| Q2 | exit=1 / exit=2 区分：PARSE_ERR_* 是 parse 失败（exit 2）还是 check 失败（exit 1）？| SRS 编码表：exit 1 = 编译期检查 FR-CHECK-*；exit 2 = parse 失败 FR-PARSER-*。Racket main.rkt L90 `(exit 2)` 在 parse handler；L168 `(exit 1)` 在 check exn handler。fallback 分支对应：PARSE_ERR_MEMORY_AUTO_APPEND（FR-PARSER-3）→ exit 2，但 SRS IF-CLI-1 exit 1 必须测，所以 exit 1 case 用** malformed check 错误**：在 .al 里写 `(define-agent (bad-name ...))`（括号错或 on-failure 非法枚举 "UNKNOWN_STRATEGY"）触发 FR-CHECK-1/2/3 → exit 1 |
| Q3 | exit≥4 怎么构造才能不影响其他文件？| 方式：fallback 分支 `python -c "import sys;sys.exit(5)"`，路径 A（racket 在）新建临时 racket 文件 `(error 'test-panic)| 临时文件，再 `racket tmp_path/panic.rkt` → exit 非 0/1/2/3 → `assert returncode >=4` |
| Q4 | 7 flags 扫描 `-V` racket 不存在 → fallback 扫什么？| 扫 3 源：`compiler/main.rkt` command-line 段字符串（已 `--check-only/--json-errors/-i/-o` 4 个长/短）+ `pyproject.toml [project].version` + `runtime/checker.py` 顶部 `__version__`（如果没有则用 pyproject 就够，≥7 个关键词命中）|

---

*END OF SPEC.*
