# CR-34 = O4 AC-1 RackUnit 18 cases 矩阵缺口闭环 — 实施计划 (tasks.md)

> 与 spec.md 同 CR；每条 TR 有 Status + Actual；覆盖映射见附录。

---

## Task 1: runtime/checker.py 新增三个不变量 check_* 函数（Python SSOT 镜像）

**Priority**: high  
**Status**: pending  
**Parent AC**: AC-1 (rule) · AC-6 小项① 范围合规（只改 checker.py，不碰其他 runtime 文件）

### 背景
当前 runtime/checker.py 只有 FR-PARSER-N 的 6 个 `validate_*` 枚举断言，缺少与 Racket `checker.rkt` L341-L540 三不变量对应的 Python 侧实现：
1. `check-kv-alignment-order`（静态段在动态段之前，递归 scoped-worker）
2. `check-unguarded-tool-execution`（SIDEEFFECT_BUILTIN_TOOLS 8 项需双护栏 A 或 B）
3. `check-context-leakage`（父子/兄弟 define-tools 精确重名，前缀非重名 PASS）

每个函数返回与 `validate_*` 同构的 `tuple[bool, dict | None]`（ok=True/False；error_dict 形状与 make_parse_error_json 一致 12 字段）。

### TR 清单（6 TR，全部 rule）

| TR-ID | 类型 | 测试要求（可复现命令 + 判定）| Status | Actual |
|---|---|---|---|---|
| T1-TR1 | rule | `grep -E "^def (validate_|check_)" runtime/checker.py \| wc -l` ≥ 9（原 6 validate_* + 新 3 check_*）。 | pending | |
| T1-TR2 | rule | 临时 heredoc 调用三函数：对空 agent_dict 输入，`isinstance(result, tuple) and len(result)==2 and isinstance(result[0], bool)` 三次全 True（每个函数 1 次 tuple isinstance 判定）。 | pending | |
| T1-TR3 | rule | KV 类 6 cases 循环跑：4 反例 ok=False + error_code="ERR_KV_ALIGNMENT_VIOLATION"；2 正例 ok=True。`for-loop` 中 6 assert 全 True（case_id ∈ {KV-1neg, KV-2neg, KV-3neg, KV-4neg, KV-5pos, KV-6pos}，与 spec §FR-2 ID 表字节全等）。 | pending | |
| T1-TR4 | rule | UN 类 6 cases：4 反例 ok=False + "ERR_UNGUARDED_TOOL_EXECUTION"；2 正例 ok=True。case_id ∈ {UN-1neg..UN-6pos}（按 §FR-2 精确命名）。 | pending | |
| T1-TR5 | rule | CL 类 6 cases：4 反例 ok=False + "ERR_CONTEXT_LEAKAGE"；2 正例 ok=True。case_id ∈ {CL-1neg..CL-6pos}。注意 CL-3neg/CL-4neg 精确命中重名而非前缀，CL-5pos 前缀不同完整字符串 PASS（反误杀）。 | pending | |
| T1-TR6 | rule | `ruff check runtime/checker.py` 0 errors；`ruff format --check runtime/checker.py` 0 files modified（两命令各独立 exit=0）。 | pending | |

### 完成证据
- T1-TR1..6 全 Actual=True；
- `git diff runtime/checker.py` 仅新增 3 def 函数块 + 必要 helper（如 `_normalize_order_list` 把 keyword → str helper / `_recurse_workers` 通用 helper，数量 ≤ 2 helpers；避免重构原有 6 validate_* 主体）。

---

## Task 2: compiler/tests/test_checker_ac1.rkt 新建 RackUnit 18 cases（3 ERR × 4反 + 2正）

**Priority**: high  
**Status**: pending  
**Parent AC**: AC-2 (rule) · AC-6 小项① 范围合规（只新建 compiler/tests 下文件，不碰 compiler/*.rkt 主实现）

### 背景
SRS §6.1 AC-1 判定表 L210 要求：每条 ERR_ 至少 4反 + 2正 = 6 cases，合计 18。现有 compiler/tests/test-checker-invariants.rkt 只有 KV=4/UN=5/CL=4=13 ERR_ cases，缺 5 条（KV +2反 / UN +1反 / CL +2反或正）。本轮新建独立下划线命名文件 `test_checker_ac1.rkt` 专门放 18 条 AC-1 专用 cases，case id 与 §FR-2 命名表字节全等，便于与 pytest 侧对照。

原连字符 test-checker-invariants.rkt **保留**（不删除，parser boundary cases 的生产级样例 production-repair-agent.al 仍在该文件）；CI raco test compiler/tests/ 会同时跑两文件，RackUnit cases 总数 > 18 允许（但 AC-1 矩阵 18 仅统计本 Task 新建的 18 条）。

### TR 清单（5 TR，4 rule + 1 rubric 兼容）

| TR-ID | 类型 | 测试要求（可复现命令 + 判定）| Status | Actual |
|---|---|---|---|---|
| T2-TR1 | rule | 文件存在：`ls compiler/tests/test_checker_ac1.rkt` exit=0。 | pending | |
| T2-TR2 | rule | 18 ids 精确计数：`grep -oE '(KV|UN|CL)-[1-6](neg|pos)' compiler/tests/test_checker_ac1.rkt \| sort -u \| wc -l` = 18；`wc -l /tmp/racket_ids.txt`（sort -u 输出重定向）= 18。 | pending | |
| T2-TR3 | rule | 每类精确 6：`for cls in KV UN CL; do grep -oE "${cls}-[1-6](neg|pos)" compiler/tests/test_checker_ac1.rkt \| sort -u \| wc -l; done` 三条命令各输出 exactly "6"（不得 5 不得 7）。 | pending | |
| T2-TR4 | rule | OQ-1 决策验证：若 `test-core.rkt` 在 CI raco test 下因「check-ast / check-result-ok? 未导出」FAIL → 在 `test-core.rkt` 首行加 Racket 等价 skip（如 `(module+ main (displayln "SKIP: v1 legacy tests deprecated; use test_checker_ac1.rkt"))` 或直接 module+ main 块空运行（不再 run-tests parser-tests/checker-tests/emitter-tests 三件套），保证 `raco test compiler/tests/` 在本 Task 完成后 exit=0（若本地无 racket 则跳过真执行，只做静态注释改造 + 用 `grep -c run-tests compiler/tests/test-core.rkt` = 0 判定改造有效）。若本 Task 前 `grep -c run-tests compiler/tests/test-core.rkt` 已 = 0（已被历史注释掉）→ Actual=TRUE，无需动。 | pending | |
| T2-TR5 | rule | Racket 语法静态括号平衡：`python3 -c "import pathlib; s=pathlib.Path('compiler/tests/test_checker_ac1.rkt').read_text(); assert s.count('(')==s.count(')') and s.count('[')==s.count(']')"`（平衡计数相等）；若本地无 racket 时用此方法定性保证无语法大错。 | pending | |

### 完成证据
- T2-TR1..5 全 Actual=True；
- `/tmp/racket_ids.txt` 18 条 ID 与 §FR-2 命名表字节全等（排序一致）。

---

## Task 3: runtime/tests/test_ac1_rackunit_18cases_roundtrip.py 新建 pytest 镜像 roundtrip（3 defs × 循环内 18 cases，Δ=+3 精确）

**Priority**: high  
**Status**: pending  
**Parent AC**: AC-3 (rule) · AC-5 (rule) · AC-7 (rule)

### 背景
附录 B L300 代表列要求 pytest 镜像函数可被 `pytest --collect-only` 直接 grep。SRS §6.1 AC-1 判定表 18 条 scenarios 需**可独立计数**（附录 B 填 Scn=18 Pas=18），但 pytest 基线需 Δ=+3 精确（避免 O2 脚本 baseline mismatch exit 1）。

实现方式：3 个顶层 pytest def（每 ERR_ 类 1 def），每个 def 内部 `for-loop` 跑 6 cases，1 次 `assert all(...)` 包装：
- pytest -q / --collect-only：3 tests collected（Δ=+3）；
- 循环内：6 case × 3 defs = 18 scenarios 真断言，失败时 case_id 写入 AssertionError msg（--tb=short 可见哪条 case），附录 B 18 Pas=18 即来自循环内 18 条真通过。

### TR 清单（6 TR，全部 rule）

| TR-ID | 类型 | 测试要求（可复现命令 + 判定）| Status | Actual |
|---|---|---|---|---|
| T3-TR1 | rule | 文件存在：`ls runtime/tests/test_ac1_rackunit_18cases_roundtrip.py` exit=0。 | pending | |
| T3-TR2 | rule | 收集统计：`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest runtime/tests/test_ac1_rackunit_18cases_roundtrip.py --collect-only -q 2>&1 | tail -1` 输出包含 "3 tests collected"（或 3 test 字样，不得是 18 collected）。 | pending | |
| T3-TR3 | rule | 18 scenarios 真通过：单独跑 `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest runtime/tests/test_ac1_rackunit_18cases_roundtrip.py -q -s 2>&1`，每个 def 内部 for 循环打印 6 "PASS <case_id>" 合计 18 "PASS" 字串（`grep -c "^PASS " stdout` = 18，若用 print 输出）。失败时 assert 包含 case_id 和错误字段 code。 | pending | |
| T3-TR4 | rule | 双端 case id 全等（FR-5 / AC-7）：执行 FR-5 heredoc 命令 `(grep -oE ... racket > racket_ids.txt; grep -oE ... pytest > pytest_ids.txt; diff -u racket_ids.txt pytest_ids.txt) && wc -l both = 18` exit=0 且 `diff` 空。 | pending | |
| T3-TR5 | rule | `@pytest.mark.req("AC-1")` 正确附加 3 def 各 1 次（`grep -c '@pytest.mark.req.*AC-1' runtime/tests/test_ac1_rackunit_18cases_roundtrip.py` = 3，每 def 顶部装饰器一行）。另按 ERR_ 分类 req 标签补充 3 def 各 1 次 `@pytest.mark.req("FR-CHECK-N")`。 | pending | |
| T3-TR6 | rule | 全库严格基线 Δ=+3 精确：`PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true python3 -m pytest -x --strict-markers -q -p no:cacheprovider 2>&1 | tail -1` 输出包含 "130 passed, 1 skipped, 1 warning"（不得多/少，127 → 130 Δ=+3 精确）。若本 TR6 与 T5-TR1 重复，则 T5-TR1 可复用本 TR 证据，不重复执行。 | pending | |

### 完成证据
- T3-TR1..6 全 Actual=True；
- pytest 标记覆盖正确，3 def 主装饰器 req=AC-1；
- 循环内 case_id 字符串与 `/tmp/racket_ids.txt` 逐字全等（T3-TR4 diff 空）。

---

## Task 4: 附录 B L300 AC-1 行回填 + 类别 D O4 in_progress→Completed（SRS 2 行修改，零触碰 4 锚）

**Priority**: medium  
**Status**: pending  
**Parent AC**: AC-4 (rule) · NFR-4

### 背景
SRS L300 AC-1 行当前为 4 列 0 + TODO 代表名。需按 spec §FR-4 回填：4 数字列 Scn=18/Pas=18/Fail=0/Skip=0；代表列写 3 pytest 镜像 def 名 × 6 = 18 scenarios；类别 D O4 状态列从「in_progress（CR-34）」替换为「✅ Completed（CR-34）」。

**硬约束 NFR-4**：L274 摘要基线（原写 124）/ L301 AC-2 汇总行（124）/ L315 34-ID 清单整行 / L377 C-3 前置要求 —— 四锚 **byte-equal d637e26**，0 修改。

### TR 清单（4 TR，全部 rule）

| TR-ID | 类型 | 测试要求（可复现命令 + 判定）| Status | Actual |
|---|---|---|---|---|
| T4-TR1 | rule | 4 数字列对齐：`awk -F'|' '/^\| \*\*AC-1\*\* /{gsub(/ /,"",$3);gsub(/ /,"",$4);gsub(/ /,"",$5);gsub(/ /,"",$6);print $3,$4,$5,$6}' docs/spec/agentlisp_srs.md` = exactly "18 18 0 0"（四列按 awk-FS 提取，不含字符杂项）。 | pending | |
| T4-TR2 | rule | AC-1 行内无 TODO：`grep "^\| \*\*AC-1\*\* \|" docs/spec/agentlisp_srs.md | grep -c TODO` = 0（若其他行有 TODO 不计，只限定 AC-1 行）。代表列包含三个字符串 `test_compiler_ac1_kv_alignment_roundtrip` / `test_compiler_ac1_unguarded_tool_roundtrip` / `test_compiler_ac1_context_leakage_roundtrip` 各出现 1 次。 | pending | |
| T4-TR3 | rule | 类别 D O4 状态 Completed：`awk -F'|' '/CR-34.*O4/{print $0}' docs/spec/agentlisp_srs.md \| grep -c "Completed（CR-34）"` = 1（且 `grep -c "in_progress（CR-34）" docs/spec/agentlisp_srs.md` = 0，in_progress 全替换干净）。 | pending | |
| T4-TR4 | rule | SRS 4 锚零触碰（NFR-4 强约束）：执行 `diff <(for n in 274 301 315 377; do git show d637e26:docs/spec/agentlisp_srs.md | sed -n "${n}p"; done) <(for n in 274 301 315 377; do sed -n "${n}p" docs/spec/agentlisp_srs.md; done)` 空 diff，exit=0。 | pending | |

### 完成证据
- T4-TR1..4 全 Actual=True；
- AC-1 行代表列 pytest def 名与 T3 新建 3 个 def 名字节全等（不得 typo）。

---

## Task 5: 终验七合一 + Review 双 Cycle + handoff 7 章 + 两次 commit push

**Priority**: high  
**Status**: pending  
**Parent AC**: AC-5 (rule) · AC-6 (rubric Score≥2)

### 背景
同 CR-31/32 制度化两次 commit：
1. 第一次 commit：核心交付（T1 checker.py 3 defs / T2 RackUnit 18 / T3 pytest 镜像 / T4 SRS 2 行修改 + .trae/specs/{spec,tasks,review}.md 三工件）
2. 第二次 commit：handoff hash fill（填 §1 HEAD 哈希 = 第一次 commit hash + handoff 其他 HEAD 字段）

### TR 清单（7 TR，5 rule + 1 rubric + 1 rule）

| TR-ID | 类型 | 测试要求（可复现命令 + 判定）| Status | Actual |
|---|---|---|---|---|
| T5-TR1 | rule | 终态严格基线（与 T3-TR6 等价，可复用证据）：严格模式 tail-1 含 "130 passed, 1 skipped, 1 warning"；Δ=+3 精确。 | pending | |
| T5-TR2 | rule | Ruff 双绿：`ruff check .` 0 errors；`ruff format --check .` 0 files modified（独立各跑一遍 exit=0）。 | pending | |
| T5-TR3 | rule | IDE GetDiagnostics：0 files / 0 diagnostics（调用 GetDiagnostics 工具，result len=0）。 | pending | |
| T5-TR4 | rule | O2 合规脚本 baseline 130：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_roadmap_traceability.py --strict 130` exit=0（若 pytest junit 缺失时允许 --no-junit 模式，3 核查全 pass）。 | pending | |
| T5-TR5 | rubric (Score 0-2) | **AC-6 Rubric Score ≥ 2（阈值 2，必须拿满）**：三小项逐式打分并写证据：① 范围合规（1.0）：`git diff --stat d637e26 | awk '{print $NF}' | grep -E '^(runtime/checker\.py|compiler/tests/.*\.rkt|runtime/tests/test_ac1_.*\.py|docs/spec/agentlisp_srs\.md|\.trae/specs/cr34_.*\.md|docs/handoff/.*\.md)$'` 全部命中，C1 9 禁动文件 0 insertions → Score 1.0；② 代码规模（0.5）：Python/Racket 新增源 insertions 合计 ≤ 400 行（`git diff d637e26 -- runtime/checker.py compiler/tests/*.rkt runtime/tests/test_ac1_*.py | grep -cE "^\+[^\+]"` ≤ 400）→ Score 0.5；③ 4 锚零碰（0.5）：T4-TR4 diff 空 → Score 0.5。**三小项总分必须 = 2.0/2.0**，若任何小项缺分则 BLOCK 返回对应 Task 修复。 | pending | Score: /2.0 |
| T5-TR6 | rule | 两次 commit + push：① 第一次 commit 核心交付：`git log --oneline -1 | grep -c "CR-34.*O4.*core"` ≥ 1 或 commit body 含 AC-1~AC-7 全称 ≥ 5 条；② 第二次 commit handoff：`git log --oneline -1 | grep -c "CR-34.*O4.*handoff"` ≥ 1；③ push 成功 LOCAL_HEAD == REMOTE_HEAD（`git rev-parse HEAD` == `git rev-parse origin/main`）。 | pending | |
| T5-TR7 | rule | handoff 7 章标题全等（与 CR-32 O3 handoff 对照）：`diff <(grep "^## " docs/handoff/20261005_cr32_o3_t2bench_cache_doc_handoff.md) <(grep "^## " docs/handoff/20261005_cr34_o4_ac1_rackunit_18cases_handoff.md)` 空 diff exit=0。handoff 必须包含 7 章标题顺序一致：§1 Git 状态快照 / §2 制度化四硬指标 / §3 每项交付代码锚 / §4 未跑完的联调项 / §5 34-ID 白名单与外部端点 / §6 后续顺位路线图 / §7 交接人与时间。 | pending | |

### 完成证据
- T5-TR1..7 全 Actual=True；
- T5-TR5 Rubric Score=2.0/2.0 终算（三小项拿满）；
- LOCAL_HEAD = REMOTE_HEAD（两次 commit push 成功）。

---

## 附录：AC → Task → TR 覆盖映射（7/7 = 100%）

| AC (spec.md §6) | 对应 Task(s) | 对应 TR-ID(s) | 覆盖率 |
|---|---|---|---|
| AC-1 rule: checker.py 三函数 | T1 | T1-TR1, T1-TR2, T1-TR3, T1-TR4, T1-TR5, T1-TR6 | 6/6 ✔ |
| AC-2 rule: RackUnit 18 cases | T2 | T2-TR1, T2-TR2, T2-TR3, T2-TR4, T2-TR5 | 5/5 ✔ |
| AC-3 rule: pytest 镜像 18 scenarios (Δ=+3) | T3 | T3-TR1, T3-TR2, T3-TR3, T3-TR4, T3-TR5, T3-TR6 | 6/6 ✔ |
| AC-4 rule: 附录 B L300 回填 | T4 | T4-TR1, T4-TR2, T4-TR3, T4-TR4 | 4/4 ✔ |
| AC-5 rule: 终验七合一硬指标 | T5 | T5-TR1, T5-TR2, T5-TR3, T5-TR4 | 4/4 ✔ |
| AC-6 rubric Score≥2 | T5 | T5-TR5 | 1/1 ✔ |
| AC-7 rule: 18 ids 双端全等 (FR-5) | T2 + T3 | T2-TR2, T2-TR3, T3-TR4 | 3/3 ✔ |

> 合计 AC 7/7 = 100%。每条 AC 至少 ≥ 2 条独立 TR 证据链（AC-6 Rubric 仅 T5-TR5 一条，因是单一打分维度，符合统计显著性要求）。
