# CR-41 No-PyPI SDD 总体规划 - Implementation Plan（不依赖 PyPI 的任务分解，严格依赖序 1→22）

## Priority Order Legend（执行顺序不跳）
P0 = **不可绕过**（BLOCK 期间先完成，4 件 ≤ 2h 工作量）；P1 = **主线**（10 宏 V2.1 三绿闭环，预计 2-3 天）；P2 = **收尾/文档**（回退树补齐、基线升级、CI 验证，1 天）。

---

## Task 1：HAN-GAP-01 修复：Handoff 远期 18→16 口径统一（3 处改字）
- **Status**: `completed`
- **Priority**: P0（必做 01/04，≤ 10 分钟）
- **Depends On**: None
- **Description**:
  - 把 handoff 文档中所有「远期 18 件」「剩余 18 件」统一改为「远期 16 件（21 件设计模式总清单 - MVP 5 件已实现）」。
  - 三处必改锚：§8 三射表第 8 号行；§6.2 中顺位 1 CR-42 启动描述；§9.1 GAP 登记 HAN-GAP-01 条目。
  - §9.2 回退树对应 HAN-GAP-01 行补 Cause（口算多加了 2 件=planner/reflect 宏拆成 2 种分类重算了）+ Fix 本 Task 执行证据。
- **Acceptance Criteria Addressed**: AC-4（HAN-GAP-01 修复 rule）；AC-10（合规零回退）；AC-9（可追溯三射表 ≥4）
- **Test Requirements**:
  - `rule` TR-1.1: `grep -cE "远期.*18件\|远期.*18 件\|18件未实现\|剩余 18 件" docs/handoff/20261006_cr40_o13_stage0_and_stage1_tdd_red_handoff.md == 0`
  - `rule` TR-1.2: `grep -c "远期 16 件" 上述文件 >= 3`
  - `rule` TR-1.3: check_handoff_compliance exit=0（改字不破坏 7 章结构）
- **Completion Evidence**: TR-1.1 PASS 远期18件grep count=0；TR-1.2 PASS 远期16件 grep count=4；TR-1.3 PASS check_handoff_compliance exit=0 (110.8KB handoff)。
- **Notes**: 不涉及任何 SRS/代码/CI 变动；C1 diff=0 自动维持。

---

## Task 2：CR-41 SRS 孤儿登记 + check_roadmap_traceability ID_RE 扩（10 新 FR-ID）
- **Status**: `completed`
- **Priority**: P0（必做 02/04，≤ 30 分钟）
- **Depends On**: Task 1
- **Description**:
  - SRS [L324 孤儿列表](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L324-L324)（38-ID）末尾裸逗号追加 **10 个 CR41-PAT 新 ID：CR41-PAT01/CR41-PAT02/CR41-PAT03/CR41-PAT04/CR41-PAT05/CR41-PAT06/CR41-PAT07/CR41-PAT08/CR41-PAT09/CR41-PAT10 → 总 48-ID）。
  - 附录 B 矩阵新增 10 行（CR41-PAT01..10），每条绑定 10 个 A 包新宏对应；Scn=0/Pas=0（先占位，Task 11 落地后置 Scn/Pas=3 each）。
  - 正文 §3 FR-PATTERN-02 后追加 10 行 CR41-PAT 锚点（确保 body 提取器命中）。
  - [scripts/check_roadmap_traceability.py L30-L34](file:///Users/lee/products/agentLisp/scripts/check_roadmap_traceability.py#L30-L34) ID_RE 正则扩 `CR41-PAT(?:0[1-9]|10)；L72-L82 _extract_orphan_ids 正则结尾扩 `(?:IF-TEMPORAL-1|CR41-PAT\d{2})`；L106-L110 check_pattern_id_count len 从==38==→>=38（制度化可扩兼容 CR-42）。
- **Acceptance Criteria Addressed**: FR-CR41-08；AC-7（三验 exit=0）；AC-9（三射表质量）
- **Test Requirements**:
  - `rule` TR-2.1: 孤儿列表 `grep -oE "CR41-PAT[0-9]{2}" SRS.md | sort -u | wc -l == 10`
  - `rule` TR-2.2: `check_roadmap_traceability.py` exit=0（ROADMAP-ID-MISMATCH count=0，O2 rows 允差已在 CR-40c 调整 ±6 足够）
  - `rule` TR-2.3: pytest --strict baseline 仍 128/13/1（未加代码，无回归）
- **Completion Evidence** (TR-2.1 PASS count=10；TR-2.2 EXIT=0 MISMATCH=0；TR-2.3 `128 passed, 13 skipped, 1 warning`；三集合 orphan==appb==body==48 TRI_EQUAL=True。
- **Notes**: 不许给新 ID 加 Markdown `**` 包围（裸逗号格式要求）；附录 B 第一列必须与老 38 ID 严格对齐格式（粗体 ID 后空格+|，中文名称移至末列）。

---

## Task 3：release.yml 四端 Build 基线自验工作流（_tmp_cr41_release_buildcheck.yml）
- **Status**: `pending`
- **Priority**: P0（必做 03/04，≤ 1h）
- **Depends On**: Task 2
- **Description**:
  - 新建 `.github/workflows/_tmp_cr41_release_buildcheck.yml`（**不修改正式 release.yml**，C1 类允许新建临时 workflow）。
  - 触发条件：workflow_dispatch + `push tag == v2.0.0-rc5-buildcheck*`（glob）。
  - 4 个 Job 原样复制正式 release.yml 四端 Build：
    ① Windows pwsh Build（strip Racket classifier + allow-direct-references + wheel+sdist + checkout restore）
    ② Ubuntu bash Build（同上 bash 版）
    ③ macOS bash Build（同上）
    ④ publish-pypi 独立 bash Build（同上 bash 版，**不带 publish step**，只跑到 `git checkout -- pyproject.toml` 结束）
  - 每 Job 结束后 `actions/upload-artifact@v4` 上传 dist/ 产物（win-whl / ubuntu-whl-sdist / macos-whl-sdist / publish-pypi-sdist-whl 共 4 份）。
  - 打 tag `v2.0.0-rc5-buildcheck1` push 触发一次 → 收证据；任务完成后保留 workflow 文件（直到 PyPI 登录后 RC5-3 验证正式 release.yml Build 侧生效再删）。
- **Acceptance Criteria Addressed**: FR-CR41-06；AC-5（4/4 Build 全绿）；AC-10（合规零回退）
- **Test Requirements**:
  - `rule` TR-3.1: CI 4 Build jobs 全 success；无 publish-pypi OIDC claim（verify 日志中未出现 pypa/gh-action-pypi-publish@release/v1 的 OIDC token 行）
  - `rule` TR-3.2: 4 Job 日志中 ① strip classifier 执行 4× ② `allow-direct-references = true` append 4× ③ `git checkout -- pyproject.toml` 执行 4×
  - `rule` TR-3.3: 4 份 artifact `unzip -l *.whl` 中 `METADATA` classifier 列表不含 `Programming Language :: Racket`（证明 strip 生效）
  - `rule` TR-3.4: 构建后 `git diff HEAD -- pyproject.toml` 在每个 Job 日志最后一行输出为空（证明 checkout restore 生效，C1 pyproject.toml 零提交改动）
- **Notes**: `v2.0.0-rc5-buildcheck1` tag 用完不删，留在远端证明基线，不会触发制度化 rc5 永不复用（rc5 正式 tag 是 `v2.0.0-rc5`，连字符版本）。

---

## Task 4：Handoff §9.2.1 RC-41 回退树补 docker-publish + create-release 6 子节点
- **Status**: `pending`
- **Priority**: P0（必做 04/04，≤ 30 分钟）
- **Depends On**: Task 3（Task 3 失败 1-2 次可先登记 Cause/Fix，并行做 Task 4）
- **Description**:
  - handoff [§9.2 RC-5 表后](file:///Users/lee/products/agentLisp/docs/handoff/20261006_cr40_o13_stage0_and_stage1_tdd_red_handoff.md#L387-L401) 新增「§9.2.2 RC-41 Build/Docker/Release Job 回退表（制度化 6 子节点）」。
  - 6 子节点：docker login fail / docker buildx fail / docker push fail / gh release create fail / artifact upload fail / tag 格式不匹配。
  - 每条含：序号 / 现象字节级 / 常见 Cause 2 条 / 推荐 Fix 2 条 / Blocked By / Unblock Condition / FAIL≥3 总回退（跳下一版或换 trigger）。
- **Acceptance Criteria Addressed**: FR-CR41-07；AC-6（6 子节点登记）；AC-11（接手质量 §9 回退树完整）
- **Test Requirements**:
  - `rule` TR-4.1: `grep -cE "docker login fail|docker buildx fail|docker push fail|gh release create fail|artifact upload fail|tag 格式不匹配" handoff.md == 6`
  - `rule` TR-4.2: 6 条每条都包含至少 1 个 `Blocked By:` + 1 个 `Unblock Condition:` 字段（§9 结构合规）
- **Notes**: Task 4 与 Task 11-20（10 宏代码实现）完全独立，可并行做；当前 CR-40 handoff 已达 102.8KB，新增 6 行估计 +0.6KB，不会影响 size 阈值。

---

## Task 5：compiler/patterns_v2.rkt 顶层骨架（require + provide 10 宏）+ bracket=0 验证
- **Status**: `pending`
- **Priority**: P1（主线 01/10，≤ 1h）
- **Depends On**: Task 1,2,3,4 任意顺序（代码主线独立于文档/CI）
- **Description**:
  - 新建 `compiler/patterns_v2.rkt` 顶层：`#lang racket` + `(provide ... 10 宏: defpriority-agent defdecomposition-agent deffsm-agent defevaluator-agent deftopic-model-agent defdecomposer-agent defguardrails-safety-agent defhitl-agent defexception-agent defexploration-agent)`
  - 10 宏 `define-syntax` 全部暂写 `(syntax-rules () [(_ args (... ...)) (quote (TODO CR41-PAT01..10 TEMPLATE))])` 占位骨架。
  - 全局只用 `()` 括号，不用任何 `[]`（Racket 8.12 reader bug 永久规避）。
  - 跑 `_tmp_bracket_diff.py patterns_v2.rkt` 验证 bracket sq=0 par=0。
- **Acceptance Criteria Addressed**: NFR-CR41-04（bracket=0）；NFR-CR41-02（size ≤800 骨架 10% ≤80）；AC-10（合规 bracket 满分）
- **Test Requirements**:
  - `rule` TR-5.1: `(read (open-input-file "compiler/patterns_v2.rkt"))` datum 级不抛错
  - `rule` TR-5.2: `python3 scripts/_tmp_bracket_diff.py compiler/patterns_v2.rkt` → `sq=0 par=0`（精确匹配）
  - `rule` TR-5.3: 10 宏 provide 数量 = `grep -c "def.*-agent" patterns_v2.rkt provide 段` 精确 = 10
- **Notes**: 禁止 require checker.rkt（永久 C1 禁动类依赖）；可 require racket/base, racket/syntax, racket/format, racket/match 标准库。

---

## Task 6：compiler/main.rkt expand-pattern-macros 合并 V2 命名空间（不碰 C1 其他）
- **Status**: `pending`
- **Priority**: P1（主线 02/10，≤ 30 分钟）
- **Depends On**: Task 5
- **Description**:
  - [main.rkt L90-L105 v20 expand-pattern-macros](file:///Users/lee/products/agentLisp/compiler/main.rkt#L90-L105) 中 in-process ns `eval` require 段原为 `(require "patterns.rkt")` → 改为 `(begin (require "patterns.rkt") (require "patterns_v2.rkt"))`（仍在干净 make-base-namespace 中隔离，主 ns 不污染）。
  - 顶层 require 不新增 patterns_v2.rkt（只在 expand-pattern-macros 运行时干净 ns 加载，避免顶层 struct srcloc* 冲突 + C1 接口收敛）。
- **Acceptance Criteria Addressed**: FR-CR41-03（V1+V2 宏合并 ns）；NFR-CR41-01（C1 main.rkt 不在 6 禁动类清单=合法可写；checker/parser/emitter/ci.yml/pyproject 不写）
- **Test Requirements**:
  - `rule` TR-6.1: CI 原 Standalone/pytest/RackUnit V1 5 宏三绿无回归（CR-40c 基线）
  - `rule` TR-6.2: 新 Standalone 运行 `patterns_v2.rkt` 10 件骨架宏 `expand` 不抛错（返回 TODO TEMPLATE 形式，占位阶段即可）
  - `rule` TR-6.3: `racket -l compiler/main -e '(require (file "patterns_v2.rkt"))'` 主 ns require 仍被拒绝（只允许 expand-pattern-macros 隔离 eval，证明 C1 接口收敛）
- **Notes**: main.rkt 不属于 C1 6 禁动类（project_memory 中 C1 6 core = checker/parser/emitter/agentlisp_compiler/ci.yml/pyproject.toml），合法可写；已在 CR-40 O13 V1 patterns 写过，口径一致。

---

## Task 7：10 宏测试 fixture 骨架（.al + .expected.rkt 30 对 · pytest-bdd features 2 新）
- **Status**: `pending`
- **Priority**: P1（主线 03/10，TDD 先红 → 后续 Task 8-17 逐个变绿，≤ 2h）
- **Depends On**: Task 5, 6
- **Description**:
  - 新建 `tests/patterns/fixtures_v2/` 目录，放 10 × 3 fixture：
    01-10: `cr41_pat01_priority_hc.al` + `.expected.rkt`（HC FIRST 写死名 × 字节级 200chars 前缀全等 = `(define-agent cr41-priority-hc-test ...`）
    11-20: `cr41_pat01_priority_generic.al` + `.expected.rkt`（GENERIC SECOND 任意名 agent，三必块 model/tools/context 存在，idx 正）
    21-30: `cr41_pat01_priority_reverse.al` + `.expected.rkt`（FR-PATTERN-02 反序 KV 输入 → reorder 输出 model_idx<tools_idx<context_idx 升序）
  - 复用 `tests/patterns/test_pattern_checker.py` 文件级 `skipif(not HAS_RACKET)` 不变；新增 `test_pattern_checker_v2.py`，同 V1 结构：pytest-bdd Scenario 30 条（每条绑定对应 fixture），Scn=0 阶段（先红，Task 8-17 变绿后置 Scn=Pas=1）。
  - RackUnit `compiler/tests/test_patterns_v2_mvp.rkt` 10 条，每条同 V1 v25h `normalize-sexp` 口径；全部 `(check-true #f)` 占位先红。
- **Acceptance Criteria Addressed**: NFR-CR41-03（pytest 30 passed / RackUnit 10 success / Standalone 20 failures=0 目标先写 fixture；AC-8 SBE 规格质量 rubric）
- **Test Requirements**:
  - `rule` TR-7.1: pytest 初次 `python3 -m pytest tests/patterns/test_pattern_checker_v2.py --strict` = **30 failed（红阶段完成）**
  - `rule` TR-7.2: RackUnit `raco test compiler/tests/test_patterns_v2_mvp.rkt` = 10 failure(s)（红阶段完成）
  - `rule` TR-7.3: 30 份 expected.rkt 都不含 `[` 字符（全 `()`，bracket=0 口径一致）
- **Notes**: 30 failed 是目标（红阶段 TDD 证据）；不可使用 `.skip` 跳过（否则红阶段没被验证）。

---

## Task 8-17：10 宏分别实现（A 包组合逐个落盘）
> 说明：为保证每宏独立可追踪，10 个宏拆 10 个 Task，每个 Task 对应 1 件 Spec A 包模式，完成后必须触发临时 CI 跑 patterns_v2 子集变绿。

---

## Task 8：CR41-PAT01 — Priority（优先级排序）· 宏实现 + pytest/RackUnit/Standalone 3 条变绿
- **Status**: `pending`
- **Priority**: P1（主线 04/10，≤ 3h）
- **Depends On**: Task 7
- **Description**:
  - 模式说明：输入 `:priority-rules ((:model 1) (:context 0) (:tools 2))` → KV 桶内元素按 priority-value 升序重排；输出展开必须是 plist→blocks 5 桶分桶 + reorder 升序（KV Cache 前缀强对齐）。
  - `patterns_v2.rkt` `syntax-case` 实现 `defpriority-agent` HC FIRST / GENERIC SECOND 双分支匹配（first-match 顺序一致 V1）。
  - 对应 fixture 01/11/21 expected 字节级 200chars 前缀全等；Standalone `ok?=#t`。
- **Acceptance Criteria Addressed**: FR-CR41-01/02；NFR-CR41-03（3/30 PASS 累计）；NFR-CR41-07（KV 前缀对齐）；AC-1（三绿）；AC-8（SBE rubric）
- **Test Requirements**:
  - `rule` TR-8.1: Standalone expand-priority 单测 `(ok? (expand-pattern-macros forms))` = ok=#t（HC/GENERIC 双分支）
  - `rule` TR-8.2: pytest `tests/patterns/test_pattern_checker_v2.py -k priority` 3/3 PASSED（01+11+21）
  - `rule` TR-8.3: RackUnit `case CR41-PAT01 priority` MATCH?=#t actual/expected 200chars 前缀全等
- **Notes**: 不使用 subprocess，只 in-process eval 2 arg；所有 pattern 桶号严格：0=:model/1=:tools/2=:context/3=:harness/4=:multiagent（NFR-CR41-07）。

---

## Task 9：CR41-PAT02 — Decomposition（任务分解）
- **Status**: `pending`
- **Priority**: P1（主线 05/10，≤ 3h）
- **Depends On**: Task 8
- **Description**: 输入 `:decompose ((:subgoal "analyse" :steps (...)))` → 展开 2 层 scoped-worker（orchestration topology + 每个子任务 1 个 scoped-worker）；同 Task 8 三绿。
- **Acceptance Criteria Addressed**: FR-CR41-01/02；NFR-CR41-03（6/30）；AC-1；AC-8
- **Test Requirements**: 同 TR-8.1/8.2/8.3，关键词改为 decomposition 与 fixture 02/12/22。

---

## Task 10：CR41-PAT03 — FSM（有限状态机）
- **Status**: `pending`
- **Priority**: P1（主线 06/10，≤ 3h）
- **Depends On**: Task 9
- **Description**: 输入 `:fsm ((:state :init :transit ((:to :done :on "success"))))` → 展开 Harness Verify 段内置 `fsm-current-state` 原子变量 + Constrain 段列出所有状态（静态断言状态可达总数 ≥ 2）。三绿。
- **Acceptance Criteria Addressed**: 同上；累计 pytest 9/30。
- **Test Requirements**: 同 TR-8 口径，fixture 03/13/23；HC GENERIC REVERSE 3 条。

---

## Task 11：CR41-PAT04 — Evaluator（评估器）
- **Status**: `pending`
- **Priority**: P1（主线 07/10，≤ 3h）
- **Depends On**: Task 10
- **Description**: 输入 `:evaluation-criteria ((:accuracy :pass-threshold 0.8) (:safety :pass-threshold 1.0))` → 展开 Harness Correct 段 2 条 threshold 检查；model/tools/context 三必块。三绿。
- **Acceptance Criteria Addressed**: 同上；累计 pytest 12/30。
- **Test Requirements**: 同 TR-8 口径，fixture 04/14/24。

---

## Task 12：CR41-PAT05 — Topic Model（主题建模）
- **Status**: `pending`
- **Priority**: P1（主线 08/10，≤ 3h）
- **Depends On**: Task 11
- **Description**: 输入 `:topics ((:topic "fraud-detection" :keywords [...]))` → KV 桶 context 分类为 topics 子树，Tools 段注入 `scoped-worker(name=topic-processor)`。三绿。
- **Acceptance Criteria Addressed**: 同上；累计 15/30。
- **Test Requirements**: 同 TR-8 口径，fixture 05/15/25。

---

## Task 13：CR41-PAT06 — Decomposer（解析器 / 结构化提取）
- **Status**: `pending`
- **Priority**: P1（主线 09/10，≤ 3h）
- **Depends On**: Task 12
- **Description**: 输入 `:decomposer-schema ((:field :date :type iso-date) (:field :amount :type double))` → 展开 Constrain 段 2 条 `decomposer-schema-field-type-check`；Harness Verify 执行断言。三绿。
- **Acceptance Criteria Addressed**: 同上；累计 18/30。
- **Test Requirements**: 同 TR-8 口径，fixture 06/16/26。

---

## Task 14：CR41-PAT07 — Guardrails & Safety（护栏安全）
- **Status**: `pending`
- **Priority**: P1（主线 10/10，≤ 3h）
- **Depends On**: Task 13
- **Description**: 输入 `:guardrails ((:deny-topics pii))` → Harness 三段都加 guardrails 钩子；`on-violation` 参数走 Verify→Correct 回路（复用 NFR-SEC 基线）。三绿。
- **Acceptance Criteria Addressed**: 同上；累计 21/30。
- **Test Requirements**: 同 TR-8 口径，fixture 07/17/27。

---

## Task 15：CR41-PAT08 — HITL（Human-in-the-Loop）
- **Status**: `pending`
- **Priority**: P1（主线 11/10，≤ 3h）
- **Depends On**: Task 14
- **Description**: 输入 `:hitl ((:approval-gate :before "model-invoke" :role "reviewer"))` → Constrain 段 `human-approval-required-before`；Verify 段 `waiting-for-human-signal`（复用 IF-TEMPORAL-1 signal 基线）。三绿。
- **Acceptance Criteria Addressed**: 同上；累计 24/30。
- **Test Requirements**: 同 TR-8 口径，fixture 08/18/28。

---

## Task 16：CR41-PAT09 — Exception Handling & Recovery（异常恢复）
- **Status**: `pending`
- **Priority**: P1（主线 12/10，≤ 3h）
- **Depends On**: Task 15
- **Description**: 输入 `:on-failure ((:type timeout) (:retry 3) (:backoff 1.5x))` → Correct 段 3 层 `on-failure retry` 子树；Harness 流程 Constrain(declare)+Verify(check)+Correct(retry) 一层不少。三绿。
- **Acceptance Criteria Addressed**: 同上；累计 27/30。
- **Test Requirements**: 同 TR-8 口径，fixture 09/19/29。

---

## Task 17：CR41-PAT10 — Exploration & Discovery（探索发现）
- **Status**: `pending`
- **Priority**: P1（主线 13/10，≤ 3h）
- **Depends On**: Task 16
- **Description**: 输入 `:explore ((:budget 100) (:stop-criteria ((:convergence 0.001))))` → Harness Verify 段 `exploration-budget-check` + `convergence-stop-criteria` 两条；Correct 段 `expand-more-candidates`。三绿。
- **Acceptance Criteria Addressed**: 同上；累计 **30/30 PASS（AC-1 目标达成）**。
- **Test Requirements**: 同 TR-8 口径，fixture 10/20/30。

---

## Task 18：GAP-1 落地 · patterns_checker_v2.rkt 旁路模块（NFR-PATTERN-01/02）
- **Status**: `pending`
- **Priority**: P2（收尾 01/05，≤ 2h）
- **Depends On**: Task 8-17（10 宏三绿闭环后接 NFR 静态核查）
- **Description**:
  - 新建 `compiler/patterns_checker_v2.rkt`（**旁路，不 require checker.rkt**，纯 datum 级结构比对）。
  - 实现 2 个公共函数：
    ① `(check-nfr01 ast expected-datum)` → 返回 #t/#f；NFR-PATTERN-01 AST 零运行时字节级全等：同 fixture expected 字节级一致（排除 `;;` 注释）。
    ② `(check-nfr02 ast)` → 5×2 静态安全矩阵，V1 5 + V2 10 每宏都跑：`[HC|GENERIC] × {model, tools, context, harness, multiagent}` 5 桶共 10 维度 × 15 宏 = 150 检查点全部 #t。
  - 提供 `(for/list ([m macros]) ...)` 15 宏总跑；输出 report 方便 pytest 调用。
  - 接入 main.rkt expand-pattern-macros 返回值后追加调用：`(check-nfr01 ...) AND (check-nfr02 ...)` 失败时抛 `ERR_NFR_PATTERN_01_MISMATCH` / `ERR_NFR_PATTERN_02_MISSING_BUCKET`（与 V1 ERR_KV_ALIGNMENT_VIOLATION 错误码一致）。
- **Acceptance Criteria Addressed**: FR-CR41-04；AC-3（Scn=Pas=15≥15 每条宏 1 个 HC+GENERIC=2×15=30 检查点 → 每条 1 Scn，15 宏=15 Scn）；AC-2（C1 diff=0）
- **Test Requirements**:
  - `rule` TR-18.1: `check-nfr01` 对 15 宏×2=30 HC/GENERIC expected 全部 #t；故意 diff 1 字节必须返回 #f（二进制验证）
  - `rule` TR-18.2: `check-nfr02` 150 检查点 150/150 #t；故意从宏展开中移除 `harness` 桶 → 必须 fail 对应 15 checkpoints
  - `rule` TR-18.3: SRS L318 NFR-PATTERN-01 `Scn=15 Pas=15` + L319 NFR-PATTERN-02 `Scn=15 Pas=15`；check_roadmap_traceability exit=0（ScnSum=PasSum）
- **Notes**: C1 6 core diff=0 保持；patterns_checker_v2.rkt ≤400 insertions（NFR-CR41-02）。

---

## Task 19：CR-41 三验基线统一钉死（SRS L278 / handoff / pytest 锚）
- **Status**: `pending`
- **Priority**: P2（收尾 02/05，≤ 1h）
- **Depends On**: Task 18
- **Description**:
  - SRS L278 `CR39_BASELINE_PASSED_COUNT: 128` 旁新增下一行：`CR41_BASELINE_PASSED_COUNT: 158`（本机无 Racket 口径：128 原 + 30 V2 patterns = 158）；同句补「验证基线（CR-41 GA）158 passed / 3 skipped / 1 warning」。
  - `check_roadmap_traceability.py L182` 基线 OR 再升级：优先 `CR41_BASELINE_PASSED_COUNT:\s*(\d+)` > `CR39` > `pytest X passed`。
  - handoff §0 启动入口 3 命令补「pytest 期望 158 passed」；§5.5 验证基线表新增 CR-41 GA 一行。
- **Acceptance Criteria Addressed**: NFR-CR41-05（三验 exit=0 158/3/1）；AC-7（rule）；AC-9（可追溯）
- **Test Requirements**:
  - `rule` TR-19.1: 本机 pytest --strict 末尾字节级 `158 passed, 3 skipped, 1 warning`
  - `rule` TR-19.2: `check_roadmap_traceability` AC-2 Scn=Pas=基线 union_size=1（158）
  - `rule` TR-19.3: check_handoff_compliance exit=0（≥140KB 预期）

---

## Task 20：Handoff §8 三射表补 10 CR41-PAT-ID 三节点映射 + §6 顺位 CR-42 对齐
- **Status**: `pending`
- **Priority**: P2（收尾 03/05，≤ 1h）
- **Depends On**: Task 19
- **Description**:
  - §8 三射表（[handoff L341-L357](file:///Users/lee/products/agentLisp/docs/handoff/20261006_cr40_o13_stage0_and_stage1_tdd_red_handoff.md#L341-L357)）追加 10 行（序号 19-28）：每行 CR41-PAT01..10，对应 Spec 模式名、V2 宏函数名、代码路径、测试覆盖、Pass 判据。
  - §6.2 中顺位 1 CR-42 启动条件从「O13+RC4完成」更新为「CR-41 10/10 三绿 + RC5 PyPI 发布完成 OR BLOCK 解除（二选一即可启动）」。
- **Acceptance Criteria Addressed**: AC-9（三射表 ≥4）；AC-11（接手质量 rubric 5/5）
- **Test Requirements**:
  - `rule` TR-20.1: §8 三射表总行数 ≥28（原 18 + 10 新）
  - `rule` TR-20.2: `grep -c "CR41-PAT" handoff.md §8 段 == 10`
- **Notes**: 不删除原 V1 5 宏行，CR-42 启动时合并 15 件 = 完成率 71.4%。

---

## Task 21：独立 Review（CR-41 第一次 Review 闸门）
- **Status**: `pending`
- **Priority**: P2（收尾 04/05，独立 Review，不自行实现）
- **Depends On**: Task 1-20 全 completed / cancelled（无 pending/in_progress/blocked）
- **Description**: 按 Spec Mode §5 Review 闸门交给另一 Agent 独立 Review（只读权限），对照本 Spec AC-1..AC-11，每 AC 有独立证据；AC-2/10 必须零容忍 5/5。
- **Acceptance Criteria Addressed**: 所有 AC（Review 最终闸门）
- **Test Requirements**:
  - `rule` TR-21.1: Review.md 创建，AC-1..AC-11 11 条全部 pass；no 行动建议（actionable finding count=0）
  - `rule` TR-21.2: Review 结果 `pass`（不是 fail/blocked）
  - `rubric` TR-21.3: Workflow fidelity（0-2）≥ 2（Spec Mode 五阶段全走满 + Review 独立 + C1 边界严格）
- **Notes**: 必须 Fresh 上下文，与 Implementer 不同；Reviewer 不得碰 tasks.md 或 spec.md，只写 review.md。

---

## Task 22：CR-41 收尾 commit + handoff 交接章 §0.1 P3 顺位更新 + temp branch push
- **Status**: `pending`
- **Priority**: P2（收尾 05/05，最后一步）
- **Depends On**: Task 21（Review pass 之后）
- **Description**:
  - git add 所有新增/修改：compiler/patterns_v2.rkt, compiler/patterns_checker_v2.rkt, compiler/main.rkt diff, compiler/tests/test_patterns_v2_mvp.rkt, tests/patterns/*_v2*, handoff.md, SRS.md, check_roadmap_traceability.py, .github/workflows/_tmp_cr41_release_buildcheck.yml。
  - commit message 严格格式：`CR-41 <commit-short-hash>: No-PyPI 10宏(V2.1 15/21=71.4%) + GAP-1(NFR01/02 Scn=15) + HAN-GAP-01 + 四端Build自验 + handoff 140KB`；push 到 temp branch `patterns-mvp-rc40/cr40b-standalone-verify`（与 RC40 同分支，后续 RC5 用）。
  - handoff §0.1 P3 顺位表从 RC5 顺序改成「并行 CR-41 已经完成到 Task N」；§6.3 Homebrew 阻塞项更新 PyPI BLOCK + CR-41 进度。
- **Acceptance Criteria Addressed**: AC-2（C1 diff=0）；AC-7（三验 exit=0）；AC-10（合规）；AC-11（接手质量）
- **Test Requirements**:
  - `rule` TR-22.1: C1 AC-6 `git diff 03bb804 -- checker parser emitter agentlisp_compiler ci.yml pyproject.toml` stdout bytes=0
  - `rule` TR-22.2: commit 成功 push，HEAD hash 在 temp branch 可见
  - `rule` TR-22.3: handoff size ≥140KB + check_handoff_compliance exit=0
- **Notes**: 若 PyPI CONTINUE 信号在 CR-41 中途出现，本 Spec 中 P0 4 件 Task(1-4) 必须先完成，其他 Task 5-21 可以挂起先回到 RC5 流水线；队列允许半完成留 pending，但 P0 必须先交付。
