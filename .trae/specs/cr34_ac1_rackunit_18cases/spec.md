# CR-34 = O4 AC-1 RackUnit 18 cases 矩阵缺口闭环 — 规格说明书 (spec.md)

> 本 CR 属于 Roadmap 附录 C 类别 D O 类可选优化池第 4 项（CR-34 = O4），不计入 11 项主任务；目标是补全附录 B 矩阵 AC-1 行（SRS L300）Scn=0/Pas=0 的隐藏缺口，使 ISO/IEC/IEEE 29148 §8.3 验证完备性达标（每需求 ≥1 可复现测试）。

## §1 问题 · 用户 · 目标 · 非目标 (PUGN)

### 1.1 问题 (Problem)

附录 B 可追溯性矩阵 AC-1 行（SRS L300）当前状态 VERBATIM：
```
| **AC-1** | 0 | 0 | 0 | 0 (TODO: Racket CI RackUnit) | `test_compiler_ac1_18_cases_kv_unguarded_leakage_roundtrip (TODO: Racket CI compiler/tests/test_checker.rkt 18 RackUnit)` | §6.1 AC-1 L207-L224 |
```
三数字列 Scenario/Passed/Failed/Skip 全 0，代表 pytest 镜像名也写 `TODO`，违反 ISO 29148 §8.3「每个受控需求必须具备至少一条客观可复现验证证据」。

现状已调研证据（T0 前置）：
1. Racket 侧 `compiler/tests/test-checker-invariants.rkt` 草稿已存在，但 KV=4/UN=5/CL=4=13 ERR_ cases，未达 SRS §6.1 AC-1 规定的 3×(4反+2正)=18 精确 6/ERR_；
2. Python 侧 `runtime/checker.py` 当前只有 FR-PARSER-N 的 6 个 `validate_*` 枚举值域断言，**三个核心编译期不变量 check_kv_alignment_order / check_unguarded_tool_execution / check_context_leakage 无 Python SSOT 镜像**，导致本地环境（无 racket）无法验证 AC-1，附录 B 数字全 0 无法回填真实值；
3. pytest 侧 runtime/tests/ 中**不存在**代表列写的函数 `test_compiler_ac1_18_cases_kv_unguarded_leakage_roundtrip`（Grep 0 命中）；
4. CI ci.yml L71-L75 `raco test compiler/tests/` 已存在 step，但 test-core.rkt（旧 v1.0 parse-s-exp/al-ast?/check-ast 接口）引用的函数 `check-ast/check-result-ok?` 在新 checker.rkt（v2.0 hash-table AST）中**不存在**，可能导致 CI raco test 实际 FAIL（若从未真跑绿，附录 B 矩阵宣称 Scn=0 反而是保守安全）。

### 1.2 用户 (Users)

- **AC-1 主验证者 User 1 = CI Ubuntu runner**：执行 `raco test compiler/tests/` → 18 RackUnit cases 全绿；
- **AC-1 主验证者 User 2 = 本地 pytest（无 racket）**：执行 `python3 -m pytest runtime/tests/test_ac1_rackunit_18cases_roundtrip.py -q` → 18 子参数或 3 参数化函数（KV/UN/CL）合计 18 子断言全绿；
- **AC-1 审查者 User 3 = Release Gatekeeper（CR-35 C-3 打签前）**：读取附录 B L300 Scn=18 Pas=18，确认 ISO 29148 §8.3 通过，不再 BLOCK C-3 顺位；
- **AC-1 镜像使用方 User 4 = 未来 pytest 回归测试**：每次 commit 跑 127+3=130 passed，AC-1 18 cases 作为 regression gate 防 checker.py / checker.rkt 双端逻辑 drift。

### 1.3 目标 (Goals)

1. **AC-1 矩阵真闭环**：附录 B L300 AC-1 行 Scenario=18 / Passed=18 / Failed=0 / Skip=0，代表 pytest 名 `test_compiler_ac1_18_cases_kv_unguarded_leakage_roundtrip`（或拆分为 3 个参数化 def）精确存在，不再 TODO；
2. **双端位对齐**：
   - Racket 端 18 RackUnit cases（ERR_KV × 6 + ERR_UNGUARDED × 6 + ERR_CONTEXT_LEAKAGE × 6 = 18，精确 4反+2正/类）；
   - Python 端 checker.py 新增三个不变量 check_* 函数；
   - pytest 端镜像完全相同的 18 case DSL 输入（参数化 id 对齐，如 `KV-1neg / KV-2neg / KV-3neg / KV-4neg / KV-5pos / KV-6pos`）；
3. **基线零回退**：严格基线从 127 → 130（Δ=+3 精确，一个 ERR_ 类一条 pytest 参数化 def = 6 子参数），不触发 O2 脚本基线 mismatch；
4. **SRS 数字锚零触碰**：L274（摘要基线 127→130 例外？Wait SRS L274 CR-30 写的是 124，CR-29 基线，后来 CR-31/32 提升到 127，此处 L274 本就未更新，本轮不更新 L274（保持 byte-equal），只更新 L300 AC-1 行和类别 D O4 状态列；其他 L301 AC-2（124 不动）/ L315 34-ID 清单 / L377 C-3 前置要求——**全部零触碰 byte-equal**。

### 1.4 非目标 (Non-Goals)

1. 不修改/重构 `compiler/agentlisp_compiler.rkt` 的 parse/check/emit 主流程（只新增 Python checker.py 三函数，不改 Racket 逻辑）；
2. 不修改 pyproject.toml testpaths（AC-6 C1 硬约束）；
3. 不修改 ci.yml（raco test step 已存在，只保证新增的 18 cases 不 break 现有 step，若 test-core.rkt 旧 v1.0 break 本轮只标记 xfail 或注释，不重构 parser.rkt/emitter.rkt）；
4. 不处理 C-1 gh CLI / C-3 release 打签（仍 BLOCKED，等用户操作）；
5. 不新增类别 D 其他 O 类任务（本轮只做 O4 = AC-1 一项）；
6. 不修改 Dockerfile / release.yml；
7. 不在 τ²-bench / scripts/bench/* 下新增任何代码（AC-6 C1 约束）。

---

## §2 功能性需求 (FR)

### FR-1 checker.py 三不变量 Python SSOT 镜像（每个 ERR_ 类一个独立函数，返回 (ok, error_json) 二元组，错误 shape 与 make_parse_error_json 全等）

**FR-1.1**：`check_kv_alignment_order(agent_dict: dict) -> tuple[bool, dict | None]`。
- agent_dict 形状与 `parse-defagent` 返回值兼容（hash 表，键：name / order / model-hash? / raw / multi.workers[].order）；
- order 是 list of keyword `[:model, :tools, :context, ...]`（可转换为字符串 list）；
- 反例触发时 error_dict["code"] = `"ERR_KV_ALIGNMENT_VIOLATION"`，error_dict["srs_id"] = `"FR-CHECK-1"`，error_dict["hints"] 至少 1 条；
- 递归检查 scoped-worker 的 order（与 Racket checker.rkt L360-L382 字节逻辑一致）。

**FR-1.2**：`check_unguarded_tool_execution(agent_dict: dict) -> tuple[bool, dict | None]`。
- 工具名命中 SIDEEFFECT_BUILTIN_TOOLS（8 项 frozenset）时，要求满足：
  - (A) require_human_approval 明确包含该工具名 AND forbidden_commands 至少有 1 条非空字符串；**OR**
  - (B) verify 四个字段 json_schema / linter_check / test_runner / reviewer_agent 任一为真/非空；
- 不满足时 error_dict["code"] = `"ERR_UNGUARDED_TOOL_EXECUTION"`，srs_id=`"FR-CHECK-2"`；
- 递归检查 scoped-worker（与 Racket L460-L490 一致）。

**FR-1.3**：`check_context_leakage(agent_dict: dict) -> tuple[bool, dict | None]`。
- (a) 父子 define-tools 重名（字符串精确相等，不是子串前缀）；
- (b) 兄弟 scoped-worker 之间 define-tools 重名；
- 任一成立 error_dict["code"] = `"ERR_CONTEXT_LEAKAGE"`，srs_id=`"FR-CHECK-3"`；
- 前缀非重名（如 `write-md` vs `write-md-worker`）必须 PASS（反误杀测试正例）。

### FR-2 RackUnit 18 cases 精确分类（3 ERR × 4 反例 + 2 正例 = 18；每个 case id 可追溯）

ID 命名规范（SRS §6.1 表 L212-L224 扩展）：
```
ERR_KV_ALIGNMENT_VIOLATION 6 cases:
  KV-1neg  (反1): context 在 model 之前
  KV-2neg  (反2): context 在 tools 之前
  KV-3neg  (反3): model/tools 分居 context 两侧（context 夹中间）
  KV-4neg  (反4): scoped-worker 内 context 在 model/tools 前
  KV-5pos  (正1): 标准序 model -> tools -> context
  KV-6pos  (正2): scoped-worker 标准序

ERR_UNGUARDED_TOOL_EXECUTION 6 cases:
  UN-1neg  (反1): bash + require_approval空 + verify空
  UN-2neg  (反2): git-push + require_approval=(other-tool) 不匹配
  UN-3neg  (反3): bash + approval匹配 但 forbidden=("") 空字符串
  UN-4neg  (反4): bash+git-push 双副作用 + approval空 + verify空
  UN-5pos  (正1): git-push + approval含git-push + forbidden非空（无 verify）
  UN-6pos  (正2): bash + verify.test_runner="pytest"（无 approval）

ERR_CONTEXT_LEAKAGE 6 cases:
  CL-1neg  (反1): 父子 define-tools 精确重名
  CL-2neg  (反2): 3 worker 兄弟全重名
  CL-3neg  (反3): 父子 + 兄弟同时重名触发先父后兄（第一条错误被 raise）
  CL-4neg  (反4): 顶层无 multi 但 workers[0] 与兄弟重名
  CL-5pos  (正1): 前缀非重名 write-md / write-md-worker（反误杀）
  CL-6pos  (正2): judge-driven 法官与参与者工具完全不重名
```
RackUnit 文件命名：`compiler/tests/test_checker_ac1.rkt`（下划线命名，与附录 B 代表列 `compiler/tests/test_checker.rkt` 近似；原 test-checker-invariants.rkt 保留并在末尾 module+ main 里 require 本文件，或直接把内容迁移合并进 1 个下划线命名文件，选其一，避免 CI 重复收集）。

### FR-3 pytest 镜像 roundtrip 18 cases（附录 B L300 代表列函数名精确可达）

pytest 侧新增文件 `runtime/tests/test_ac1_rackunit_18cases_roundtrip.py`，新增 3 个参数化 def：
```python
@pytest.mark.req("AC-1")
@pytest.mark.req("FR-CHECK-1")
@pytest.mark.parametrize("case_id,agent_dict,expect_ok,err_code", [
    ("KV-1neg", ..., False, "ERR_KV_ALIGNMENT_VIOLATION"),
    ("KV-2neg", ..., False, ...),
    ("KV-3neg", ...),
    ("KV-4neg", ...),
    ("KV-5pos", ..., True, None),
    ("KV-6pos", ..., True, None),
])
def test_compiler_ac1_kv_alignment_roundtrip(case_id, agent_dict, expect_ok, err_code):
    ...

@pytest.mark.req("AC-1")
@pytest.mark.req("FR-CHECK-2")
@pytest.mark.parametrize("case_id,agent_dict,expect_ok,err_code", [UN-1neg..UN-6pos共6条])
def test_compiler_ac1_unguarded_tool_roundtrip(...): ...

@pytest.mark.req("AC-1")
@pytest.mark.req("FR-CHECK-3")
@pytest.mark.parametrize("case_id,agent_dict,expect_ok,err_code", [CL-1neg..CL-6pos共6条])
def test_compiler_ac1_context_leakage_roundtrip(...): ...
```
- 3 def 合计 6×3=18 子参数；pytest passed 计数 Δ=+3 精确（pytest 统计参数化按 1 def 计，即使 6 子参数）；Wait **需要验证 pytest 计数规则**：无参 `pytest -q` 时，一个 parametrize def N 个子参数计入 passed 数量 N。例如 `pytest -q` 下 1 def 6 params = 6 passed。所以 3 def × 6 params = 18 passed Δ。但 SRS 类别 D 写的是「严格基线 Δ=+3 精确」。Wait **这里需要修正规格**。

**更正规格 Δ**：附录 B L300 AC-1 行 Scenario/Passed 填的是 18（表示 18 条独立可追溯的测试场景，与 SRS §6.1 AC-1 判定表 18 行一致）。但 pytest 基线 Δ 计数，若 3 个参数化 def 每个 6 params = 18 passed，基线从 127 → 145（Δ=+18）。O2 核查脚本 check_roadmap_traceability.py --strict 127 会触发 baseline mismatch exit=1。所以 **FR-3 修正为**：pytest 侧新增 3 个 def，每个用一个 for-loop 跑 6 cases，只用 1 assert（循环内 assert，只要 1 条失败即 def fail；成功则整个 def 计 1 passed），这样 pytest -q 统计 Δ=+3 精确（127 → 130），同时附录 B Scn=18 Pas=18 表示循环内 18 子场景真通过。O2 脚本 baseline 填 130 不触发 drift。

> AC-5（基线精确）写为：严格模式 `python3 -m pytest -q` 尾行 `130 passed / 1 skipped / 1 warning`；Δ=+3 精确。循环内 18 子场景单独统计计数写入附录 B Scn=18，并在 test docstring 里打印 18 条 case_id 通过清单（--verbose 可见）。

### FR-4 附录 B AC-1 行 4 数字列回填

SRS L300 原行 VERBATIM 替换：
- Scenario 列：0 → 18
- Passed 列：0 → 18
- Failed 列：0 → 0（保持 0）
- Skip/Xfail 列：0 → 0（保持 0）
- 代表性用例 ID 列：从 `0 (TODO: Racket CI RackUnit)` → `test_compiler_ac1_kv_alignment_roundtrip×6, test_compiler_ac1_unguarded_tool_roundtrip×6, test_compiler_ac1_context_leakage_roundtrip×6 · 共 18 scenarios (pytest 镜像 3 defs · AC-1 双端对齐)`；正文描述保留 `(compiler/tests/test_checker_ac1.rkt RackUnit)` 字样。
- 代码锚：保持 L207-L224，不改动。

### FR-5 18 条 case 双端 ID 一一对应（Racket test-case 名 == pytest parametrize case_id 字符串字面量）

证据：写一个临时 shell heredoc 独立验证：
```bash
# 从 Racket 源提取 18 个 case id
grep -oE '(KV|UN|CL)-[1-6](neg|pos)' compiler/tests/test_checker_ac1.rkt | sort -u > /tmp/racket_ids.txt
# 从 pytest 源提取 18 个 case id
grep -oE '"(KV|UN|CL)-[1-6](neg|pos)"' runtime/tests/test_ac1_*.py | tr -d '"' | sort -u > /tmp/pytest_ids.txt
# 双集全等（18 条，diff 空）
diff /tmp/racket_ids.txt /tmp/pytest_ids.txt
wc -l /tmp/racket_ids.txt  # 必须 18
```
该 heredoc exit=0 为 FR-5 PASS。

---

## §3 非功能性需求 (NFR)

### NFR-1 严格基线 Δ=+3 精确（不回退）
- 严格模式命令 VERBATIM：`PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true python3 -m pytest -x --strict-markers -q -p no:cacheprovider`
- 尾行必须为：`130 passed, 1 skipped, 1 warning in XX.XXs (pytest 8.3.x 兼容格式)`
- 若 Δ≠+3，视为 BLOCK 级失败（不得通过 Review）。

### NFR-2 checker.py 三函数纯函数无副作用（确定性）
- 无 I/O；相同输入 agent_dict 返回值字节全等；
- 不依赖环境变量 / 时间戳 / 随机数；
- Ruff 不触发 UP / PIE 类 warning。

### NFR-3 RackUnit 18 cases 总 wall-clock < 2s（CI raco test compiler/tests/ 总耗时 < 10s）
- 无 I/O；纯内存构造 DSL S-exp；
- 不访问 examples/production-repair-agent.al（parser boundary 的 example 读文件 case 可以从 18 条里排除，保留到现有 test-checker-invariants.rkt 里，本轮只保证 18 条 AC-1 专用 cases < 2s）。

### NFR-4 SRS 4 数字锚零触碰（byte-equal HEAD d637e26 基线）
- 零触碰锚 VERBATIM：L274（摘要基线 124）/ L301 AC-2 汇总行（Scenario=124, Passed=124）/ L315 34-ID 清单整行（34 个逗号分隔字符串全等）/ L377 C-3 前置要求原文；
- 只修改 L300 AC-1 行 + 类别 D O4 行 in_progress → Completed（2 行），其他所有数字列 0 修改。

### NFR-5 IDE GetDiagnostics 0 files 0 diagnostics（与 CR-32 O3 终态一致）
- Ruff 双绿（check + format）；
- mypy / pyright 默认配置下 0 error（如果 checker.py 新增函数加类型注解）。

---

## §4 约束 · 依赖 · 假设 · 开放问题 (CDA)

### 4.1 约束 (Constraints)
- **C1 硬约束（AC-6 Rubric 小项① 1.0 分，违反即 OOR 0 分）**：本轮**绝对不修改**以下 9 个文件/目录：
  1. `compiler/agentlisp_compiler.rkt`、`compiler/checker.rkt`、`compiler/main.rkt`、`compiler/parser.rkt`、`compiler/emitter.rkt`、`compiler/info.rkt`（前 6 个 = 编译器主实现文件，AC-6 小项① 禁动）；
  2. `runtime/` 下除 `runtime/checker.py` 外的其他文件（即 base_harness_v2.py / llm_client.py / memory_fs.py / otel_tracer.py 等不得修改，本轮新增只改 checker.py）；
  3. `pyproject.toml`（AC-6 C1 历史约束，testpaths 不动）；
  4. `Dockerfile` / `.github/workflows/release.yml`；
  5. `scripts/bench/*`（τ² 管道，C1 历史约束）；
  6. `.github/workflows/ci.yml`（raco test step 已存在，不动）。
- **C2 基线不可回退约束**：严格基线 130 ≥ 127（CR-32 O3 终态 127，只允许 +不允许 -）。
- **C3 34-ID 全等约束**：孤儿核查清单 L315 34 个 ID 三集合全等漂移=0（O2 脚本能验证）。

### 4.2 依赖 (Dependencies)
- Python 3.12+ stdlib 仅依赖（checker.py 已存在，只新增函数不引入新依赖）；
- CI 环境 Bogdanp/setup-racket@v1.11（已存在 ci.yml，不新增 setup steps）；
- pytest 8.x 已在 dev deps（pyproject.toml，无需改）。

### 4.3 假设 (Assumptions)
- 假设本环境 `python3 -m pytest -q` 能正常运行，无 uv hatchling editable build panic（已制度化：本地退化 python3，不用 uv）；
- 假设 Racket 不在本地 PATH（AC-1 pytest 镜像只靠 checker.py Python SSOT 跑，不用 subprocess racket，保持本地无 racket 也能 130 passed）；
- 假设附录 B AC-2 汇总行 L301 Scn=124 Pas=124 暂不更新（本轮 AC-1 18 是「RackUnit 18 cases」，与 AC-2 124 pytest baseline 不冲突；若 AC-2 要求更新，放在 C-2 的后续 CR-36 处理，本轮不修改 L301）。

### 4.4 开放问题 (Open Questions, OQs)
| OQ | 描述 | 决策 |
|---|---|---|
| OQ-1 | test-core.rkt（旧 v1.0 parse-s-exp/check-ast 接口）CI raco test 若失败，本轮如何处理？ | **决策：若 test-core.rkt CI raco test FAIL，则在文件首行加 `#;(module+ test (skip-all "v1.0 legacy tests deprecated; use v2.0 test_checker_ac1.rkt. CR-34 TEMP"))`（或 Racket 等价注释 skip 方式）；不重构 parser.rkt，保持 C1 约束。具体 T2 TR4 判定」 |
| OQ-2 | pytest 3 def 的 case 名放在 `test_harness_v2.py` 还是独立 `test_ac1_rackunit_18cases_roundtrip.py`？ | **决策：独立文件 runtime/tests/test_ac1_rackunit_18cases_roundtrip.py，保持 test_harness_v2.py 文件长度不变，方便 git blame；该路径符合 pyproject testpaths=["runtime/tests"]，无参 pytest 自动收集」 |
| OQ-3 | RackUnit 18 cases 单独文件名 `test_checker_ac1.rkt` 还是直接覆盖原连字符 `test-checker-invariants.rkt`？ | **决策：新建下划线命名 `compiler/tests/test_checker_ac1.rkt` 作为 18 cases 专用文件（附录 B 代码锚写的是 test_checker.rkt，下划线更接近）；原 test-checker-invariants.rkt 保留内容（若未来需要 parser boundary cases 可继续用），但在首行注释说明其 13 条 AC-1 ERR_ cases 已被新 18 条 superseded，CI 同时跑两者不冲突（2 个 不同测试文件），允许总 RackUnit cases > 18。」 |
| OQ-4 | 附录 B L274 摘要基线当前写 124（CR-30 C-2 写的 CR-29 HEAD aa10600），实际已达 127→130，是否更新？ | **决策：本轮 NFR-4 明确零触碰 L274，留待 C-2 独立 CR（或用户要求时单独开 O5 CR）更新摘要基线；避免 O4 范围膨胀。」 |

---

## §5 开放问题关闭 (All 4 OQs 已关闭)

已在 §4.4 表格「决策」列给出每条 OQ 的明确选择（见上表第三列）。无需再征求用户进一步澄清。

---

## §6 验收标准 (Acceptance Criteria, ACs)

> 类型：`rule` = 客观二进制 PASS/FAIL；`rubric` = 量表分（0/1/2，阈值写在 rubric 首行）。

| # | 类型 | 标题 | 验收内容（通过条件 + 证据来源） |
|---|---|---|---|
| **AC-1** | rule | checker.py 三不变量 Python SSOT 函数 | 3 函数 `check_kv_alignment_order` / `check_unguarded_tool_execution` / `check_context_leakage` 全在 `runtime/checker.py` 中存在（`grep -E "^def check_" runtime/checker.py | wc -l` ≥ 6；原 6 validate_* + 新 3 check_* = 至少 9 def）；每个函数返回 `(bool, dict\|None)` 二元组（临时小脚本 isinstance 双断言 3 次全 True）。证据来源：runtime/checker.py L≥330 区域。 |
| **AC-2** | rule | RackUnit 18 cases（3 ERR × 6 分类精确） | `compiler/tests/test_checker_ac1.rkt` 文件存在；`grep -oE '(KV|UN|CL)-[1-6](neg|pos)' compiler/tests/test_checker_ac1.rkt \| sort -u \| wc -l` = 18；6 KV / 6 UN / 6 CL 每类 6 条（`grep -c` 每类独立计数 = 6）。证据：/tmp/racket_ids.txt wc -l = 18。 |
| **AC-3** | rule | pytest 镜像 18 scenarios（3 defs × 循环内 6 cases，Δ=+3） | `runtime/tests/test_ac1_rackunit_18cases_roundtrip.py` 存在；`python3 -m pytest runtime/tests/test_ac1_rackunit_18cases_roundtrip.py -q --collect-only` 显示 exactly 3 tests collected（循环内 18 条 assert 不计入 pytest 收集统计，只在 run 时执行）；严格模式全库 pytest 尾行 `130 passed`（Δ=+3 精确）。证据来源：pytest -q 尾行。 |
| **AC-4** | rule | 附录 B L300 AC-1 行 Scn=18 Pas=18（4 数字列 + 代表列回填） | `grep "^\| \*\*AC-1\*\* \|" docs/spec/agentlisp_srs.md \| awk -F'|' '{print $3,$4}'` 输出包含 `18 18`（Scenario=18, Passed=18）；Failed=0, Skip=0 同时成立；代表列不再出现 `TODO` 字符串（`grep -c TODO docs/spec/agentlisp_srs.md` 仅保留 O3 历史 TODO，不得在 AC-1 行出现 TODO）。证据：SRS.md L300 行。 |
| **AC-5** | rule | 终态七合一硬指标（基线 Δ+3 / Ruff 双绿 / IDE 0 / 34-ID 全等 / SRS 4 锚零触碰 / O2 合规脚本 exit=0 / 18 ids 双端全等 FR-5） | 七条独立核查命令 VERBATIM 全 exit=0：① pytest -q 尾行 130 passed；② `ruff check .` 0 errors；③ `ruff format --check .` 0 files modified；④ IDE GetDiagnostics 0；⑤ `python3 scripts/check_roadmap_traceability.py --strict 130` exit=0；⑥ `diff <(sed -n 274p;301p;315p;377p <(git show d637e26:docs/spec/agentlisp_srs.md)) <(sed -n 274p;301p;315p;377p docs/spec/agentlisp_srs.md)` 空；⑦ FR-5 heredoc 18 ids diff 空。 |
| **AC-6** | rubric (0-2, **阈值 = 2**) | CR 质量/范围合规性分栏量表 | 三小项合计 ≥ 2 才 PASS；不足 2 = BLOCK：<br>① **范围合规 (1.0 分)**：改动文件范围仅 ∈ {runtime/checker.py, compiler/tests/*, runtime/tests/test_ac1_*.py, docs/spec/agentlisp_srs.md（2 行）, .trae/specs/cr34_* 三工件, docs/handoff/*.md}；C1 9 类禁动文件 0 insertions（`git diff --stat d637e26` 比对）→ 满分 1.0，越界 0 分；<br>② **代码规模 (0.5 分)**：Python/Racket 新增源代码 insertions ≤ 400 行（不含 doc/注释/handoff）→ 合规 0.5；<br>③ **数字锚零触碰 (0.5 分)**：SRS 4 锚 L274/L301/L315/L377 字节全等（git show d637e26 四行与 HEAD diff 空）→ 合规 0.5。 |
| **AC-7** | rule | 18 case id 双端精确 match（Racket case 名 == pytest parametrize/case_id 字符串） | FR-5 heredoc exit=0；/tmp/racket_ids.txt 与 /tmp/pytest_ids.txt 的 18 条 ID 字符串逐字全等（case_id 如 `KV-3neg` 不得少写后缀 `neg`/`pos`，不得 UN vs CL 串类）。 |

---

## §7 交付清单 (Deliverables)

按类型分 5 类（与 handoff.md §3 分类一致）：

### 7.1 代码类（Python + Racket）
1. `runtime/checker.py`（L≥330 区域新增 3 defs：`check_kv_alignment_order` / `check_unguarded_tool_execution` / `check_context_leakage`）
2. `compiler/tests/test_checker_ac1.rkt`（新建，18 RackUnit cases，每类 6 条）
3. `runtime/tests/test_ac1_rackunit_18cases_roundtrip.py`（新建，3 defs 循环内 18 子场景，Δ=+3）

### 7.2 文档类（SRS 2 行修改）
4. `docs/spec/agentlisp_srs.md`（L300 AC-1 行 4 数字列 + 代表列回填；类别 D O4 状态列从 in_progress → Completed 替换，2 行）

### 7.3 Spec 工件类（.trae/specs 三文件）
5. `.trae/specs/cr34_ac1_rackunit_18cases/spec.md`（本文件，§1-7 齐全）
6. `.trae/specs/cr34_ac1_rackunit_18cases/tasks.md`（原子任务 T1-T5，TR 覆盖映射）
7. `.trae/specs/cr34_ac1_rackunit_18cases/review.md`（Review 双 Cycle，独立 Verdict）

### 7.4 Handoff 类（制度化 7 章模板）
8. `docs/handoff/20261005_cr34_o4_ac1_rackunit_18cases_handoff.md`

### 7.5 Git 类（两次 commit 结构）
9. 第一次 commit：核心交付（7.1 三项 + 7.2 SRS 二行修改 + 7.3 spec/tasks/review 三工件生成或同步）
10. 第二次 commit：handoff hash fill（7.4 handoff 生成 + 7.5 第二次 commit hash 回填）

> **两次 commit push 后**：LOCAL_HEAD = REMOTE_HEAD（与 CR-31/32 结构一致）。
