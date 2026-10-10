# CR-41 No-PyPI SDD 总体规划 - Product Requirements Document（不依赖 PyPI 登录/OIDC 发布的全部主线支线工作合并排期）

## Overview
- **Summary**：在 PyPI RC5-2 「Owner=4TWS3 登录 Pend Pub 两端账号」BLOCK 期间，把所有不依赖 PyPI 登录 / OIDC 发布 / Warehouse API 的主线与支线工作统一规划为 **CR-41**，按规范驱动开发 (SDD + SBE + TDD + 三表交叉核查) 推进；一旦 PyPI 登录恢复 CONTINUE，立即切换回 RC5-2→RC5-3→RC5-4→RC5-5 主流水线打签，两条流水线不互相占用 C1 禁动类 6 core。
- **Purpose**：消除 BLOCK 期间的空转；把 16 件未实现设计模式 + SRS 2 个 GAP (NFR-PATTERN-01/02) + 文档 1 个 GAP (HAN-GAP-01 远期 18/16 漂移) + release.yml CI 四端自验 build 基线 + handoff 失败回退树补全，统一打包为一个可追溯的 Spec，供其他 Coding Agent 零上下文移交。
- **Target Users**：接手 CR-41 的其他 Agent（需能读 SRS + 写 patterns V2 Racket 宏 + pytest + RackUnit）；最终用户：基于 AgentLisp 的 Agent 开发者（使用更多 Pattern Macro 快速装配复杂流程）。

## Goals
1. **G0 交付速度**：在 BLOCK 解除前（PyPI 登录恢复）完成 **P0+P1 10 项任务**（预计占 CR-41 总工作量 80%）。
2. **G1 模式覆盖率**：Pattern 设计模式从 5 / 21 → **15 / 21（71.4%，不含 6 件 Phase3 RSI 远期件）**；新增 10 件 V2.1 宏全部三绿闭环（pytest + Standalone + RackUnit）。
3. **G2 SRS 无缺口**：消除 GAP-1（NFR-PATTERN-01/02 Scn=Pas=0 → ≥15）、GAP-3（handoff docker+create-release Job 回退树缺位）、HAN-GAP-01（18/16 漂移）；附录 B 38→48 个 SRS-ID 100% 有三射映射。
4. **G3 合规零回归**：C1 禁动类 6 core（checker/parser/emitter/agentlisp_compiler/ci.yml/pyproject.toml）diff=0；AC-6 新增 patterns_v2.rkt insertions ≤800；所有新增宏 bracket=0；三验（check_roadmap_traceability / check_handoff_compliance / pytest --strict）exit=0。
5. **G4 CI 自验基线**：release.yml 四端 Build step（Windows pwsh/Ubuntu bash/macOS bash/publish-pypi bash）strip Racket classifier + allow-direct-references 双工作区改，在无 OIDC/publish step 触发的条件下跑通一次独立验证（tag v2.0.0-rc5-buildcheck1），4/4 Build jobs 全绿（3 端 whl+sdist 产出件字节级存在 + git checkout -- pyproject.toml 后 pyproject.toml diff=0）。

## Non-Goals
1. **绝对不碰**：PyPI OIDC 打签（RC5-3/4/5 全停，等待 CONTINUE）；Pending Publisher 账号级录入（Agent 侧不代填）。
2. **绝对不碰**：C1 禁动类 6 core 清单。若 GAP-1 NFR-PATTERN-01/02 落地必须接 checker/emitter 时，**新建 `compiler/patterns_checker_v2.rkt` 旁路模块**，完全不依赖/修改 checker.rkt。
3. **不推进**：Phase 3 RSI（Spec L375-L395 远期 6 件模式：Learning/Adaptation/Evaluation/Monitoring/Resource-Aware/E2E Benchmark），留在 CR-42 远期。
4. **不创建**：Pattern 宏实现文档、README 变更、Wiki（除非 handoff §0.1/§6 明确要引用）。
5. **不引入**：新第三方库；新子进程调用（Racket subprocess API 永久弃用，所有隔离继续用 in-process make-base-namespace + eval 2 arg）。

## Background & Context
1. 项目硬约束来源：[project_memory.md §硬约束 + CR-40 handoff §C1 禁动清单](file:///Users/lee/products/agentLisp/docs/handoff/20261006_cr40_o13_stage0_and_stage1_tdd_red_handoff.md)。
2. Pattern 21 件清单来源：[agentlisp-pattern-macros-tech-spec.md §3.1-3.5 L60-L234](file:///Users/lee/products/agentLisp/docs/agentlisp-pattern-macros-tech-spec.md#L60-L234)。
3. 当前 SRS 缺口锚点：[agentlisp_srs.md L316-L319 FR/NFR-PATTERN 01/02](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L316-L319) + [L324 38-ID 孤儿列表](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L324-L324)。
4. 本 Spec 不替换 SRS，只补充 CR-41 内部编号；所有新增 FR-ID 必须同时登记到 SRS 孤儿列表裸逗号行。

## Functional Requirements
- **FR-CR41-01**：提供 `patterns_v2.rkt` 新增第 8 个 compiler 模块，**至少包含 10 件新宏**（见 Spec §3 优先组合 A 包）：defpriority/decomposition/fsm/evaluator/topic-model/decomposer/guardrails-safety/hitl/exception-handling/exploration-discovery 共 10 件高层宏 provide 暴露。
- **FR-CR41-02**：每件新宏支持 HC FIRST → GENERIC SECOND 双分支（同 O13 5 宏口径，HC=写死名宏展开字节级前缀全等；GENERIC=任意名展开三必块存在）。
- **FR-CR41-03**：main.rkt `expand-pattern-macros` in-process eval 隔离模块同时 require V1 patterns.rkt + V2 patterns_v2.rkt（合并宏命名空间，无冲突）。
- **FR-CR41-04**：GAP-1 落地：新建 `patterns_checker_v2.rkt` 旁路模块实现 NFR-PATTERN-01（AST 零运行时字节全等）和 NFR-PATTERN-02（5×2 静态安全矩阵：HC/GENERIC × 5 Top-level bucket），不依赖 checker.rkt。
- **FR-CR41-05**：HAN-GAP-01 修复：handoff §8 第 8 号行「远期 18 件」改为「远期 16 件（21 - 5 MVP）」，同步 §6.2 中顺位 1 描述、§GAP 登记、下一 CR-42 启动口径统一。
- **FR-CR41-06**：release.yml 基线自验：新增临时工作流 `.github/workflows/_tmp_cr41_release_buildcheck.yml`（不替换 release.yml 正式版），触发条件 = workflow_dispatch 或 push tag `v2.0.0-rc5-buildcheck*`，只跑 Build step ×4（Windows/Ubuntu/macOS/publish-pypi Build）**不跑 publish step**；验证后可由 Agent 删除。
- **FR-CR41-07**：handoff §9.2.1 回退树补 docker-publish Job + create-release Job 两大 Job 大类（共 6 个子失败节点：docker login fail / docker buildx fail / docker push fail / gh release create fail / artifact upload fail / tag 不匹配）。
- **FR-CR41-08**：新增 10 个 FR-ID 在 SRS 孤儿列表 38-ID→39-ID..48-ID 登记为裸逗号（无 ** 包裹）；同步 check_roadmap_traceability.py ID_RE 扩（PATTERN\d|CR41-PAT\d）。

## Non-Functional Requirements
- **NFR-CR41-01**：C1 禁动类 6 core `git diff HEAD --stat -- checker parser emitter agentlisp_compiler .github/workflows/ci.yml pyproject.toml` 严格 = 0 行改动（rule AC-6 审计 PASS）。
- **NFR-CR41-02**：`patterns_v2.rkt insertions ≤800`（AC-6 扩展预算；10 宏 × 平均 70 行 = 700，100 行裕度）；`patterns_checker_v2.rkt ≤400 insertions`。
- **NFR-CR41-03**：10 新宏 pytest ×2 每条（HC+GENERIC）共 20 cases + 继承 FR-PATTERN-02 reorder 反序 10 cases = pytest patterns_v2 子集 `30 passed`；Standalone 10×2=20 failures=0；RackUnit 10 success(es)；三绿稳（V25h 口径）。
- **NFR-CR41-04**：10 新宏每个 `(read form) → bracket diff sq=0 par=0`（Racket 8.12 reader 深嵌套方括号已永久弃用，V2 继续全局 `[→(` `]→)` 100% 圆括号）。
- **NFR-CR41-05**：三验 exit=0：check_roadmap_traceability / check_handoff_compliance / pytest --strict（本机无 Racket 机器输出 `158 passed, 3 skipped`；有 Racket CI `188 passed, 3 skipped`，与 CR-41 基线行钉死）。
- **NFR-CR41-06**：交付 handoff CR-41 版 ≥140KB，必须包含 §0 启动入口、§8 三射表（SRS 48-ID 全覆盖）、§9 回退树（覆盖 10 新宏 + Build×4/Docker/Release 6 Job）。
  - **状态（2026-10-11）**：内容判据 **达成** —— §0 ✓、§8 ✓、§9 ✓（本轮补 RC-5 发布结果与 6 节点回退树）；**体积判据未达成**：实测 61,238 B < 140 KB。
  - **建议修订**：删除字节数判据，改为「§0/§8/§9 三节齐备 + 每节含可复核锚点」的内容清单判据。理由：字节数可用冗余文字注水，与文档可用性无因果关系；本 handoff 保留精简形态。
- **NFR-CR41-07**：所有新增宏的 PList→Blocks 升序严格 `:model(0)<:tools(1)<:context(2)<:harness(3)<:multiagent(4)`，确保 KV 静态前缀强对齐与 V1 5 宏口径完全一致。

## Constraints
- **技术**：Racket 8.12 只能跑 CI ubuntu-latest；所有 Racket 验证必须推到 temp branch 的 CI 运行，本机无 Racket 运行时。永久禁用 subprocess API，只用 in-process eval 2 arg（见 CR-40 永久诊断）。
- **业务**：PyPI 任何打签动作必须等 CONTINUE 信号，CR-41 结束前不能产生任何 OIDC 发布流量；版号 `v2.0.0-rc5`（正式）永不打两次，buildcheck tag 只能用 `v2.0.0-rc5-buildcheckN`（N=1,2,3…≥3 次 fail 也不会触发制度化永不复用 rc5）。
- **依赖**：无新增 PyPI 依赖（hatchling build 不变；pytest / pytest-bdd / rackunit 复用）。
- **C1 硬约束红线**：`compiler/checker.rkt` / `compiler/parser.rkt` / `compiler/emitter.rkt` / `compiler/agentlisp_compiler.rkt` / `.github/workflows/ci.yml` / `pyproject.toml` 绝对不写，哪怕一行都不行（AC-6 审计零容忍）。

## Assumptions
1. **A1**：PyPI 登录 BLOCK 持续时间 ≥3 天（否则 CR-41 可能仅完成 P0 3 项就被 CONTINUE 中断，P1 7 项顺延 CR-42）。
2. **A2**：CI 配额（GitHub Actions Ubuntu/macOS/Windows runner）充足，buildcheck 每次 ≤60min，不会被调度队列延迟 >24h。
3. **A3**：GAP-1 落地的 patterns_checker_v2.rkt 旁路方案能完整复现 checker.rkt FR-CHECK-1/2 断言机制，不需要访问 checker 内部 struct（永久弃用 srcloc* 预编译，V2 用 read 后 datum 级纯结构比对）。
4. **A4**：10 新宏的 GENERIC 展开不与 V1 5 宏冲突（provide 全部用独立 defX-agent 名，无同名覆盖）。

## Open Questions（Approve 前需要用户 4TWS3 拍板）
- **[ ] Q1**：10 件新宏 **优先组合 A 包**（本 Spec FR-CR41-01 默认）是否合适？还是想换其他 10 件（如 3.4 安全护栏优先 / 3.5 Multi-Agent 家族优先）？
  - A 包默认清单：Priority / Decomposition / FSM / Evaluator / TopicModel / Decomposer / Guardrails-Safety / HITL / ExceptionHandling / ExplorationDiscovery（10 件，覆盖 Spec 5 大类每类至少 1-2 件）
- **[ ] Q2**：GAP-1 落地（NFR-PATTERN-01/02 Scn=Pas=0→≥15）是否同意**旁路方案**（新建 patterns_checker_v2.rkt 不碰 checker.rkt C1 禁动类）？还是需要正式豁免 C1 修改 checker 接线？
- **[ ] Q3**：CR-41 三验基线是否钉死为本 Spec NFR-CR41-05 的 158/3/1（本机无 Racket）/ 188/3/1（有 Racket）？还是等 A 包全部跑过后动态调整？
- **[ ] Q4**：CR-41 命名空间合并（FR-CR41-03）后，`define-agent` 顶层语法糖是否要加 `:pattern-version (v1\|v2\|mix)` 参数？还是直接 mix 透明加载（当前默认透明）？

## Acceptance Criteria

### AC-1：Pattern V2.1 10 宏三绿闭环
- **Type**: `rule`
- **Given**: temp branch HEAD = commit 包含 `compiler/patterns_v2.rkt` 10 新宏 + tests 用例
- **When**: CI 触发 `_tmp_o13_patterns_mvp_verify.yml`（扩展支持 V2 patterns）
- **Then**: 日志满足 3 条 VERBATIM 字节级条件（AND 关系）
- **Pass Condition**: ① Standalone `failures=0/20`（10 宏×HC/GENERIC 双分支）② pytest patterns_v2 子集 `30 passed, 0 failed` ③ RackUnit `10 success(es) 0 failure(s) 0 error(s) 10 test(s) run` ④ workflow 总 `conclusion=success`
- **Evidence**: `gh run view <RID> --log` 精确 grep 4 条件各命中 1 次

### AC-2：C1 禁动类 6 core diff=0（AC-6 零容忍）
- **Type**: `rule`
- **Given**: CR-41 最后 commit HEAD
- **When**: `git diff 03bb804 --stat -- compiler/checker.rkt compiler/parser.rkt compiler/emitter.rkt compiler/agentlisp_compiler.rkt .github/workflows/ci.yml pyproject.toml`（03bb804 = CR-40 结束时 6 core 基线锚）
- **Then**: 输出严格空（0 行 6 文件）
- **Pass Condition**: stdout bytes == 0 AND exit=0
- **Evidence**: 命令 + 空输出字节级原文（AC-6 审计）

### AC-3：GAP-1 落地 NFR-PATTERN-01/02 Scn=Pas=0 → ≥15
- **Type**: `rule`
- **Given**: SRS L318 NFR-PATTERN-01 / L319 NFR-PATTERN-02 + patterns_checker_v2.rkt 旁路模块生效
- **When**: `check_roadmap_traceability.py` 跑完
- **Then**: NFR-PATTERN-01 `Scn=15 Pas=15`；NFR-PATTERN-02 `Scn=15 Pas=15`；ScnSum=PasSum
- **Pass Condition**: grep `NFR-PATTERN-01\|NFR-PATTERN-02` 在附录 B 返回 `Scn=15 / Pas=15` 各 1 次
- **Evidence**: check_roadmap_traceability 原文摘录 + 锚定 commit hash

### AC-4：HAN-GAP-01 修复 18→16（远期数量对齐）
- **Type**: `rule`
- **Given**: handoff 最新版
- **When**: `grep -nE "远期.*18件\|远期.*18 件\|18件未实现"` handoff.md
- **Then**: 输出严格空（所有远期登记统一为 16 件口径）
- **Pass Condition**: `(远期登记数=16) AND grep 18件 count=0`
- **Evidence**: grep 空输出 + handoff §8 第 8 号行 + §6.2 中顺位 1 + §GAP 登记 3 处原文摘录字节级 16

### AC-5：release.yml 四端 Build 自验 4/4 全绿
- **Type**: `rule`
- **Given**: `.github/workflows/_tmp_cr41_release_buildcheck.yml` 存在 + push tag `v2.0.0-rc5-buildcheck1`
- **When**: CI run 完成
- **Then**: 5 jobs（Windows Build / Ubuntu Build / macOS Build / publish-pypi Build / create-release-prep）= 4/4 success（Create Release 可能被 trigger 跳过不计）；且每 Build step 日志中 ① `sed/PowerShell strip Racket classifier` 执行 ② `allow-direct-references` append ③ 构建后 `git checkout -- pyproject.toml` 执行 ④ pyproject.toml diff=0 四步各命中 1 次；4 whl+sdist 产出件字节级存在
- **Pass Condition**: `conclusion=success AND jobs.*Build (success×4) AND strip classifier×4 AND checkout -- pyproject.toml×4`
- **Evidence**: `gh run view <RID> --json jobs | jq` + 4 份 artifact zip SHA256

### AC-6：handoff §9.2/9.2.1 Docker + Create Release 回退树补齐
- **Type**: `rule`
- **Given**: handoff 最新版
- **When**: `grep -cE "docker login fail|docker buildx fail|docker push fail|gh release create fail|artifact upload fail|tag mismatch"` 回退表
- **Then**: count ≥6（6 个子失败节点全部登记，每个有 2 个 Cause / 2 个 Fix 步骤，含 §9.2.1 RC-41 新表）
- **Pass Condition**: count=6 AND 每条都有 `Blocked By` + `Unblock Condition` 字段
- **Evidence**: grep count=6 + §9.2.1 RC-41 回退表原文 6 行摘录

### AC-7：三验 exit=0（pytest + roadmap + handoff）
- **Type**: `rule`
- **Given**: CR-41 最后 commit HEAD，本机无 Racket macOS
- **When**: 顺序执行 `pytest --strict → check_roadmap_traceability → check_handoff_compliance`
- **Then**: exit=0 × 3 AND pytest `158 passed, 3 skipped, 1 warning` 字节级全等
- **Pass Condition**: `$?=0 × 3` AND pytest 末尾一行字节级 158/3/1
- **Evidence**: 3 命令 exit code 记录 + pytest 尾部行字节级（V25h 归一化口径）

### AC-8：Pattern V2.1 完整性（rubric 质量）
- **Type**: `rubric`
- **Dimension**: CR-41 A 包 10 新宏的 SBE 实例化规格质量
- **Scale**: 0-5
- **Anchors**: 1 = 只有宏 define-syntax，没有 .al/.expected.rkt fixture；3 = 10 宏各 1 条 HC fixture + 1 条 GENERIC fixture，无反序 reorder；5 = 10 宏各 2 条 + 反序 reorder 10 条 = 30 cases 全部有字节级 200 chars 前缀全等；宏展开错误时定位 messages 具体到 srcloc 行号列号
- **Pass Threshold**: ≥ 4
- **Evidence**: pytest -v 输出 patterns_v2 30 用例明细 × 1 份，RackUnit expected/actual 200 chars 前缀 diff 0 字节记录 × 10 份

### AC-9：可追溯性与三射表质量（rubric）
- **Type**: `rubric`
- **Dimension**: SRS ↔ Spec ↔ Handoff 三射矩阵可追溯度
- **Scale**: 0-5
- **Anchors**: 1 = 只有 SRS 登记孤儿，handoff §8 未同步；3 = SRS orphan + handoff §8 三射表有 70% 条目；5 = SRS 孤儿 10 条新增裸逗号行 + check_roadmap_traceability ID_RE 通过 + handoff §8 三射表所有 48-ID 100% 三节点字节级对拍 + 5/5 C1 GAP 无缺口
- **Pass Threshold**: ≥ 4
- **Evidence**: §8 三射表总行数 ≥48 + 每个 CR41-PAT-ID 有对应 FR-ID + Handoff ID 的 1:1:1 映射；check_roadmap_traceability ROADMAP-ID-MISMATCH count=0

### AC-10：合规与零回退质量（rubric）
- **Type**: `rubric`
- **Dimension**: CR-41 产物对 C1 禁动类 + bracket 0 + 版号永不复用 + skip-existing:false 制度的遵守度
- **Scale**: 0-5
- **Anchors**: 1 = C1 至少 1 行改动 / bracket sq>0 / 出现 rc5 正式 tag；3 = C1 diff=0 但 bracket 有 1 处 neg；5 = C1 diff=0 × 6 核心文件 + 10 宏 bracket sq=0 par=0 + skip-existing 制度化在 release.yml 两处都为 false（当前已修）+ 未打任何 rc5 正式 tag（buildcheck tag 单独清理）
- **Pass Threshold**: ≥ 5（必须满分，零容忍）
- **Evidence**: `bracket_diff.py patterns_v2.rkt` sq=0 par=0 输出；C1 AC-6 审计 AC-2 原文；git ls-remote --tags v2.0.0-rc5 count=0；release.yml grep skip-existing=false×2

### AC-11：文档零上下文接手质量（rubric）
- **Type**: `rubric`
- **Dimension**: CR-41 handoff 文档可接手度（下一 Agent 30s 启动三命令能跑 7/10 AC）
- **Scale**: 0-5
- **Anchors**: 1 = 没有 §0 启动入口；3 = §0 存在但缺 3 命令中的 1 条；5 = §0 启动入口 3 命令字节级正确（pytest/roadmap/handoff 三验）+ §5.2 端点表包含 10 新宏 fixture 路径 + §9.2.1 回退树 RC-41 专属 10 行 + size≥140KB
- **Pass Threshold**: ≥ 5（满分，handover 合规硬要求）
- **Evidence**: handoff size=（期望 ≥140KB）原文 check_handoff_compliance 摘录；下一 Agent 接手试运行 pytest 3 命令 exit=0 记录 1 份
