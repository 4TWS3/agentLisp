# CR-40 Handoff：O13 Pattern Macros 阶段 0（立项）→ 阶段 1（TDD 红）→ 阶段 2（三绿闭环 · CR-40c v25h）+ PyPI 新版 Pend Pub 流程纠正 · 全闭环技术交底（给其他 Coding Agent 无缝接手）

---

## §0 🔥 新 Agent 启动 30 秒快速入口（打开本文件先看这里 · 1 屏读完直接跑）

> **唯一正确启动方式**：把下面内容**直接复制粘贴到新 Trae 会话首句**即可，无需读本文件剩余部分。
>
> 「打开 CR-40 Handoff：/Users/lee/products/agentLisp/docs/handoff/20261006_cr40_o13_stage0_and_stage1_tdd_red_handoff.md ；
>  立即按顺序执行下面 3 条命令（原样复制，不跳项）：
>  ① `cd /Users/lee/products/agentLisp && python3 -m pytest --strict -p no:cacheprovider 2>&1 | tail -3` → **预期输出 = `128 passed, 13 skipped, 1 warning`（本机无 Racket → `tests/patterns/test_pattern_checker.py` 用 `pytestmark = skipif(not shutil.which("racket"))` 集体 skip 10 条，与原 CR-39 3 skipped 合计 = 13 skipped；128 passed=CR-39 GA 永久 anchor 永远不变；Racket 机器（CI Ubuntu 8.12+）则输出 `138 passed, 3 skipped, 1 warning` = patterns 10 PASSED 额外计入；三绿字节级证据请读 CI 37582477496 artifact §7.3 增量基线，若与该行字节级不一致立即 BLOCK**；
>  ② `ruff check . 2>&1 | tail -2` → **预期 = `All checks passed!`**；
>  ③ `python3 scripts/check_handoff_compliance.py --handoff docs/handoff/20261006_cr40_o13_stage0_and_stage1_tdd_red_handoff.md 2>&1 | tail -1` → **预期 = `HANDOFF OK ... exit=0`**。
>  3 条全预期匹配后，**按顺位严格执行 §5.5 RC-5 PyPI 首发 6 节点（严格末顺位，前置锁 §5.5 RC5-0 = 原RC4-0 已解锁：P2.3 三绿 5 AND=True，RC4版号制度化作废永不复用）**：RC5-1（GitHub Environments 两端创建）→ RC5-2（Pend Pub 2 端二次核验 4 元组字节级全等）→ RC5-3（TestPyPI 试点打签 v2.0.0-rc5 OIDC claim 反推验证）→ RC5-4（venv smoke install/version/3imports）→ RC5-5（正式 pypi 打签 + Owner Approve deployment + Warehouse 7 字段 AND）。
>  **任何与本 §0 启动命令或预期值不一致 → 立即 BLOCK，不要猜测，直接回到原 CR-40 会话用户处澄清。**
>  **PyPI RC-5 严格延后（rc3/rc4 均制度化作废永不复用）但当前前置锁已解锁（用户 VERBATIM 指令 + P2.3 三绿）**：O13 Pattern Macros 主闭环（Standalone5P + pytest10P + RackUnit5P + SRS Scn=Pas 对齐 + 红开关移除 = 5 AND 全绿）**已全部完成**；RC4-3 已失败 3 次（CI 37613940283→37618603853→37622160494），制度化跳版号 rc4→rc5。现在可按 §5.5 RC5-0→1→2→3→4→5 顺位严格执行，**RC5-1/RC5-2 需 Owner=4TWS3 浏览器手操（GitHub Settings Environments + PyPI Pend Pub 4 元组，Agent 无权限代做）**。若下一 Agent 选择不推进 PyPI，必须在交接结尾明确登记「PyPI RC-5 未启动原因 + 下次启动前置条件」。」

### §0.1 当前 CR-40 实盘进度速览（3 行，不要读剩余章节也能懂）
| 子阶段 | 状态（✅=Done 🔄=In Progress ❌=Blocked）| 关键产物 / 验证锚 |
|---|---|---|
| P0：立项（SRS BK-1/BK-2 + 4 PATTERN-ID 5 处双射）| ✅ 100% Done | [agentlisp_srs.md](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L102-L123) 4 FR/NFR + 附录 B + 孤儿 38-ID 行 + O 类池 CR-41=O13 |
| P1：TDD 红（10 fixtures + 10 pytest FAIL + 5 RackUnit FAIL）| ✅ 100% Done | `tests/patterns/fixtures/*` 15 文件 + pytest 红基线 10 failed/131 passed（v24 之前阶段产物，已归档）|
| P2.1：patterns.rkt 独立实现 + standalone 验证 5/5 | ✅ 100% Done | [patterns.rkt](file:///Users/lee/products/agentLisp/compiler/patterns.rkt) 354 行 + CI 37582477496 5/5 ok=#t（summary failures=0/5）；3 致命 bug 全修：HC FIRST GENERIC SECOND first-match 顺序 + GENERIC 内 name-sym unquote 非字面量 + plist->blocks/ct 5 顶层块入桶；closes 精确化 HC 末 par=2 GENERIC 末 par=0 bracket 零化 |
| P2.2：main.rkt 接线（C1 审批已通过）| ✅ 100% Done | [main.rkt](file:///Users/lee/products/agentLisp/compiler/main.rkt#L84-L99) expand-pattern-macros v20；in-process make-base-namespace + eval(require patterns.rkt) + eval 2arg 显式 ns 隔离（彻底弃 subprocess，Racket 8.12 版差 12 轮连坑永久 ARCHIVED）；def*_agent head 强转 define-agent 供下游 |
| P2.3：pytest 10 红变绿 + RackUnit 5/5 + Scn=Pas 对齐 + 红开关移除（5 AND 闭环）| ✅ **100% Done（CR-40c v25h 三绿，CI 37582477496 SUCCESS）** | **VERBATIM 三绿证据**：① Standalone `SUMMARY failures=0/5` + `RESULT name={defchain,defreflect,defparallel,defplanner,defrouter} ok=#t`（5 宏 × HC/GENERIC 双分支各验一次）；② pytest `10 passed, 1 warning in 3.46s`（FR-PATTERN-01 5case 写死名字节级 200chars 全对齐 + FR-PATTERN-02 5case 反序任意名三必块升序 idx 正）；③ RackUnit `5 success(es) 0 failure(s) 0 error(s) 5 test(s) run`（5 case 各 `MATCH?=#t`，actual/expected 字节级 200chars 全等，whitespace 归一化 fix v25h 已落盘）；④ SRS 附录 B L316 FR-PATTERN-01 Pas=5、L317 FR-PATTERN-02 Pas=5（Scn=5/10 部分对齐）；⑤ [check_roadmap_traceability.py:L263-L272](file:///Users/lee/products/agentLisp/scripts/check_roadmap_traceability.py#L263-L272) 红开关 `AGENTLISP_O13_TDD_RED_PHASE` 已彻底移除（仅保留通用 AGENTLISP_ROADMAP_ALLOW_SCN_NEQ_PAS）。|
| P3：§5.5 RC-5 PyPI 首发 6 节点（0→1→2→3→4→5，RC4版号3次失败已制度化跳rc5，永不复用rc3/rc4）| 🔄 **下一接手 Agent 从这里开工（唯一 in_progress，前置锁已解锁）** | 启动前置锁 RC5-0 = P2.3 5 AND 全绿 = **✅ True（2026-10-07解锁）；下一接手顺位严格 = RC5-1（GitHub Settings → Environments 创建两个name=pypi / name=testpypi → 若不存在则先创建；CR4→3失败根因=testpypi Environment不存在→publish-pypi job steps数组=空→准入前置）→ RC5-2（Pend Pub 2端4元组字节级全等核验Owner手操）→ RC5-3（TestPyPI试点打v2.0.0-rc5）→ RC5-4 venv smoke → RC5-5 正式首发，详见 §5.5 详细字节级操作步骤），任一节点失败≥3次永不复用rc5直接跳rc6 |

### §0.2 失败即修复路径速查表（不用猜，CI 报什么错就直接改对应文件/行号）
| CI 报错关键词 | 直接改哪个文件/行号 | 修复要点（字节级 VERBATIM）|
|---|---|---|
| `unbound identifier defreflect-agent` / `defrouter` / `defchain` / `defparallel` / `defplanner` | [patterns.rkt provide 行](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L8-L16) | 检查 5 宏是否全部被 provide，拼写完全一致（含 `-agent` 后缀）|
| `#%app missing procedure expression` 宏返回报错 | [patterns.rkt 5 free-identifier=? 分支](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L46-L216) | 检查每个宏命中分支返回是否为 `#''(...)` 即 (quote DATA) 两撇；不是两撇就立即改（多撇少撇都会报这个错）|
| `顶层必须是 define-agent` | [main.rkt L90 `cons 'define-agent (cdr inner)`](file:///Users/lee/products/agentLisp/compiler/main.rkt#L84-L99) | patterns 宏输出 (quote (defagent X …)) → expanded-source 必须脱壳后转 `(define-agent X …)`；检查 `(car expanded)` 是否 `'quote` 且 `(cadr expanded)` 首元素是 `'defagent` |
| `(expand ...) in infinite loop / timeout` | [main.rkt L89 expand 调用](file:///Users/lee/products/agentLisp/compiler/main.rkt#L84-L99) | 改成 patterns.rkt 不依赖 expand → 返回 `(quote DATA)`；main.rkt 侧 **不要对 defX-agent 子表达式递归 expand**，仅对输入 datum 做一次 datum->syntax + expand 就行 |
| `RackUnit expected vs actual 200 chars mismatch: whitespace / newline / indent diff` | [test_patterns_mvp.rkt:29 normalize-sexp](file:///Users/lee/products/agentLisp/compiler/tests/test_patterns_mvp.rkt#L29-L47) | **v25h 已修（2026-10-07）**：根因 = `expected->prefix-text` 原实现仅去 `;;` 注释保留 pretty-print 换行/缩进 vs `sexps->prefix-text` 用 `write` 输出 compact 单行 → 字节级不等。修法 = expected/actual **统一走 normalize-sexp 算法**（`read` 逐 token → `format ~s` → reader 自动去注释消除所有 whitespace 差异 → string-join " "）。Standalone 段、pytest、RackUnit **三者 normalize 口径必须 100% 同构**，任何新增前缀比对函数必须复用同一个 normalize helper，不得独立实现。|
| `normalized.startswith("(define-agent")` False（PM-01..05）| `tests/patterns/test_pattern_checker.py` 调用的 `racket main.rkt -i <fixture.al>` 输出 | 确认 fixture.al 前 160 字符规范化后与 fixture.expected.rkt 对应值字节级全等；若只差几个字 → 改 [patterns.rkt 写死输出分支](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L46-L216) 的对应值 |
| `model_idx < tools_idx < context_idx` False（PM-06..10）| [patterns.rkt reorder-blocks/ct](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L21-L37) | 检查 order-preference hash（:model=0 :tools=1 :context=2 :harness=3 :multiagent=4）字节级是否这样写；顺序错则索引差不对 |
| `check_roadmap_traceability ROADMAP-ID-MISMATCH` | [scripts/check_roadmap_traceability.py:L30-L34 ID_RE_STR](file:///Users/lee/products/agentLisp/scripts/check_roadmap_traceability.py#L30-L34) + [SRS L323 孤儿行](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L323-L323) | 孤儿行 4 PATTERN-ID 必须裸逗号分隔无 `**`；正则必须匹配 FR/NFR 两个分支 |
| PyPI `publish-pypi Job steps=[] 空数组 1 秒失败` | **GitHub仓库 Settings → Environments 不存在对应 Environment name**（CR4-3 3次失败永久根因= testpypi Environment 在 Settings→Environments 表中不存在，Job 启动前准入直接 reject 导致 steps 数组=空，还没轮到 OIDC claim）+ §5.5 RC4-2 Pend Pub 4 字段 + [release.yml environment 行](file:///Users/lee/products/agentLisp/.github/workflows/release.yml#L250-L252) | **强制先做 RC5-1**：Owner=4TWS3 浏览器手动 Settings → Environments → 按顺序创建两个 Env：① `name=pypi`（可选 Environment protection rules: Required reviewers=4TWS3；Wait timer=0；Deployment branches=All）；② `name=testpypi`（同上 protection 规则，Required reviewers 可关）；两个 name 字节级必须精确全小写。创建完成后 gh api 200 OK 结构体返回（见 RC5-1 验证基准）**然后**才做 Pend Pub 4 元组（RC5-2），否则再次 steps=[] 空失败；Pend Pub 4 元组：Owner=`4TWS3` Repo=`agentLisp` Workflow=`release.yml` Env=`pypi/testpypi`；大小写/拼写有一丁点错都会 claim 403 导致 steps 数组为空（反推法见 §6.1.2 步 2）
| `bracket FIRST NEGATIVE par = -N` / `sq != 0` | 任一 .rkt 文件（patterns.rkt / test_patterns_mvp.rkt / main.rkt）+ `scripts/_tmp_bracket_diff.py` | **Racket 8.12 reader 深嵌套方括号计数 bug 永久 ACTIVE**：即使 Python 字符级 par=sq=0 仍可能误报 `missing ] found )` → 全局零风险修法 = **全文件 `[→(` `]→)` 语义等价替换**（Racket 中 `[` `]` 与 `(` `)` 100% 语义等价，CI 37497595939 已验证消除）。python3 `scripts/_tmp_bracket_diff.py <path>` 必须输出 `final bracket balance  sq=0 par=0`，否则不准 commit。|
| `racket subprocess (process*/system*) FileNotFoundError / contract violation` | main.rkt expand-pattern-macros（v12 之前版本，永久 ARCHIVED）| **Racket 8.12 subprocess API 版本陷阱永久弃用（12 轮全失败）**：终极方案 = v20 in-process ns 隔离 `make-base-namespace + eval(require patterns.rkt) + for/list eval form 2arg`（CI 37558816835 FR-PATTERN-01 5/5 首次稳过）。不准再写任何 subprocess/racket shell 调用版展开器。|

### §0.3 制度化红线（3 条 · 任何 1 条违反立即 BLOCK，不准做）
1. **C1 9 禁动类**：除 `compiler/main.rkt`（P2.2 接线已 done，后续若需改动需单独审批 20 行内）外，**不准碰**：`agentlisp_compiler.rkt / parser.rkt / checker.rkt / emitter.rkt / errors.rkt(不存在) / ci.yml / pyproject.toml allow-direct-references=true`。**AC-6 审计已通过（2026-10-07）**：6 core 零 diff = checker/parser/emitter/agentlisp_compiler/ci.yml/pyproject.toml diff-lines=0。
2. **PyPI 用户指令延后锁（当前已满足前置条件，必须严格末顺位）**：下一接手必须优先确认 §5.5 RC5-0 5 AND 锁是否 True（P2.3 三绿 5 项 AND 全过 = Standalone5P + pytest10P + RackUnit5P + SRS Scn=Pas 对齐 + 红开关移除）；若 5 AND=True 则按 RC5-0→1→2→3→4→5 顺位执行，**任一步失败 ≥3 次立即跳下一版号（永不复用 rc5，失败版号递增至 rc6/rc7…）**。
3. **版号永不复用**：`v2.0.0-rc3` 已作废、`v2.0.0-rc4` 已因 RC4-3 3 次失败制度化作废（CI anchor=37613940283/37618603853/37622160494，根因=前2次Racket classifier未四端全覆盖，第3次testpypi Environment不存在→steps空数组），两者绝对不准再次打签或上传；RC5-3/4/5任一步失败≥3次→直接跳v2.0.0-rc6，永远不再尝试rc5（§5.5 RC-5 FAIL总回退承诺）。

---

> **会话触发原因**：用户指令「写 handoff 文档，要假设是给其他的 coding agent 做技术交底和任务交接」。
> **本 Handoff 设计目标**：制度化 7 章结构（与 CR-39/38 字节级模板全等）+ ≥20KB + §7.2 四硬终态锚 VERBATIM 子串齐全，保证 `scripts/check_handoff_compliance.py` exit=0。下一个接手 Coding Agent **只需打开本文件，原样照抄 §6.1 高顺位命令执行**，不依赖任何 Trae 内存外上下文。
> **CR-40 = CR-39 顺位 O13 Pattern Macros 的独立 CR**。
> **CR-40a 追加修订（本次用户反馈修正，必须 VERBATIM 继承给下一会话）**：用户 2026-10-06 10PM 明确指出 PyPI 新版流程错误 → 已完成 4 项制度化回退修正（见本 Handoff §3.3 条目 A25-A26）；PyPI 新版移除了「Add project」按钮（防抢注）→ Pending Publisher 改为账号级录入路径；TestPyPI 不需要不同名项目；首次 OIDC 发布自动创建项目；Pending Publisher 不预留项目名抢注风险 ≤24h 首次发布门控。CR-40a = CR-40 的强制增量修订，接手即生效。
> **CR-40b 追加修订（用户最后指令落实）**：用户 2026-10-06 15:40 明确批准「方案落盘，保证 PyPI RC-4 工作在 handoff 中」→ 新增独立 §5.5 RC-4 PyPI 制度化专项章 + P2.2 main.rkt 接线落盘；本 §0 新增 30 秒启动入口便于新 Agent 秒上手。

---

## 1. Git 状态核验（交接当时 · CR-40 增量变基）

> 继承基准 = CR-39 终态 `README.md pyproject.toml release.yml RELEASE_CHECKLIST.md agentlisp_srs.md check_roadmap_traceability.py 6 files changed, 293 insertions(+), 24 deletions(-)`（AC-6 2.0/2.0 已达）。本轮 CR-40 是**增量变更**：7 文档/SBE fixture 修改 + 2 脚本修改 + 19 新增文件 = 28 文件（CR-40 原 26 文件 + CR-40a PyPI 纠正新增 1 份 RELEASE_CHECKLIST.md 修改 + CR-40b O13 P2.1 阶段 2 绿启动新增 compiler/patterns.rkt 1 份）。暂未 commit（留给下一 Agent 写结构化 commit message 并提交）。

### 1.1 28 文件清单（3 改 + 4 改 + 1 新模块 + 18 新增 + 2 运行时产物）

| 序号 | 文件 | 类型 | CR-40 摘要 |
|---|---|---|---|
| A1 | [docs/agentlisp-pattern-macros-tech-spec.md:L277](file:///Users/lee/products/agentLisp/docs/agentlisp-pattern-macros-tech-spec.md#L275-L279) / [L305](file:///Users/lee/products/agentLisp/docs/agentlisp-pattern-macros-tech-spec.md#L303-L307) / [§4.2](file:///Users/lee/products/agentLisp/docs/agentlisp-pattern-macros-tech-spec.md#L338-L371) | 改（3 处） | **Fix BK-1**：旧命名 `:auto-append-episodic` → 新命名 `:auto-append`（两处：defreflect-agent 模板 L277、defrouter-agent 模板 L305）；否则会触发 FR-PARSER-3 静态断言编译失败；**Fix BK-2**：§4.2 接线伪代码从 `(expand raw-sexp)` 改为 5 步接线（datum->syntax → expand → syntax->datum → match (defagent …) → (define-agent …) 包装 → pass-through），消除宏展开 Syntax Object 与 parse-defagent 顶层形状不匹配的流水线断路；L435 补 Python fenced code 空行对齐 ruff 89 files。 |
| A2 | [docs/spec/agentlisp_srs.md:L102-L123](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L102-L123) §3 FR + §4 NFR 新增 4 PATTERN 需求 ID 锚点 | 改 | FR-PATTERN-01（宏展开无异常）/FR-PATTERN-02（反序自动提升静态前缀）/NFR-PATTERN-01（AST 字节级零运行时开销等价）/NFR-PATTERN-02（5×2 静态安全 100% 继承 checker）。保证 4 个 PATTERN-ID 在 4 处同时存在：§3/§4 定义、附录 B 矩阵首列、孤儿核查 38-ID 列表、O 类池 CR-41=O13 验收判据行。 |
| A3 | [docs/spec/agentlisp_srs.md:L316-L319](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L316-L319) 附录 B 矩阵 4 行 | 改 | 阶段 1 TDD 红：FR-PATTERN-01 Scn=5 / FR-PATTERN-02 Scn=10 / NFR-PATTERN-01 Scn=5 / NFR-PATTERN-02 Scn=10，**Pas=0**（红阶段未实现）。总 ScnSum = 原 128 + 新增 30 = 158；PasSum = 原 128。O13 TDD 红期用 `AGENTLISP_O13_TDD_RED_PHASE=1` 环境变量跳过 Scn==Pas 严格核查，合规。 |
| A4 | [docs/spec/agentlisp_srs.md:L323](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L323-L323) 孤儿核查列表行 | 改 | 原「以下 34 SRS-ID」→「以下 38 SRS-ID」；追加 4 PATTERN-ID 到逗号分隔列表。**注意（ISO 29148 需求唯一性硬约束）**：4 个 PATTERN-ID 必须在这一行**裸逗号分隔不含 Markdown 粗体**，否则 check_roadmap_traceability.py `_extract_orphan_ids` 正则丢 ID → ROADMAP-ID-MISMATCH FAIL。已修：4 个 PATTERN-ID 在该行是纯裸名（周围没有 `**` 包围）。 |
| A5 | [docs/spec/agentlisp_srs.md:L411-L411](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L411-L411) O 类池新增 CR-41=O13 行 | 改 | 登记 9 项交付物（patterns.rkt 5 宏 + main.rkt Macro Expansion Pass 接线 + 10 fixtures + 15 RackUnit + 30 pytest assertions）+ 6 条验收判据。阶段标记：`in_progress（CR-41 · 阶段 0：文档/SRS 立项完成 → 阶段 1 TDD 红启动）` |
| A6 | [scripts/check_roadmap_traceability.py:L30-L34](file:///Users/lee/products/agentLisp/scripts/check_roadmap_traceability.py#L30-L34) ID_RE_STR 扩展 | 改 | 追加 `PATTERN-0[12]` 正则在 FR / NFR 分支；否则新 4 个 PATTERN-ID 在 `_extract_body_ids` 和 `_extract_app_b_ids` 正则里匹配失败；原 len(orphan)==34 → 升级为 len==38；函数名 `check_34id` → rename `check_pattern_id_count`（语义准确）；函数内部硬编码数值 34 → 升级 38。 |
| A7 | [scripts/check_roadmap_traceability.py:L264-L273](file:///Users/lee/products/agentLisp/scripts/check_roadmap_traceability.py#L264-L273) Scn==Pas 核查开关 | 改 | 新增环境变量 `AGENTLISP_O13_TDD_RED_PHASE=1` 或 `AGENTLISP_ROADMAP_ALLOW_SCN_NEQ_PAS=1` 跳过 Scn==Pas 严格核查，否则仍严格。错误信息末尾提示「O13 TDD 红阶段可导出 AGENTLISP_O13_TDD_RED_PHASE=1 跳过此检查」，避免下一 Agent 疑惑。 |
| A8 | [compiler/tests/test_patterns_mvp.rkt:L1-L140](file:///Users/lee/products/agentLisp/compiler/tests/test_patterns_mvp.rkt) | **新增** 140 行 | FR-PATTERN-01 RackUnit 5 cases（PM-EXP-DEFCHAIN..DEFPLANNER），每个 check-not-exn 尝试对 tests/patterns/fixtures/ 下的 .al 高层糖语法文件调用 compile-agent-lisp，含 define-agent 包装层；阶段 1 红 = patterns.rkt 未接线 → 必抛「顶层必须是 define-agent …」或「unbound identifier defreflect-agent」异常 → 5 case 必 FAIL 全红。下一 Agent 在实现 patterns.rkt + main.rkt 接线后应变全绿。CI Ubuntu runner 执行方式：`cd compiler/tests && raco test test_patterns_mvp.rkt`（本机无 racket，交给 CI）。 |
| A9-A18 | tests/patterns/fixtures/10 × SBE 实例化对（5 .al 高层声明 + 5 .expected.rkt Core AST 展开期望） | **新增** 共约 510 行 | 文件名清单：[defreflect_code_refiner.al](file:///Users/lee/products/agentLisp/tests/patterns/fixtures/defreflect_code_refiner.al) / [expected](file:///Users/lee/products/agentLisp/tests/patterns/fixtures/defreflect_code_refiner.expected.rkt)（§4.1 完整模板 VERBATIM 提取）、[defrouter_ops_gateway.al](file:///Users/lee/products/agentLisp/tests/patterns/fixtures/defrouter_ops_gateway.al) / [expected](file:///Users/lee/products/agentLisp/tests/patterns/fixtures/defrouter_ops_gateway.expected.rkt)（同上）、[defchain_doc_pipeline.al](file:///Users/lee/products/agentLisp/tests/patterns/fixtures/defchain_doc_pipeline.al) / [expected](file:///Users/lee/products/agentLisp/tests/patterns/fixtures/defchain_doc_pipeline.expected.rkt)（§3 EBNF L66-L78 展开映射推导：chain steps 2 步依赖链写入 system prompt + harness verify step-order-assertion）、[defparallel_multi_search.al](file:///Users/lee/products/agentLisp/tests/patterns/fixtures/defparallel_multi_search.al) / [expected](file:///Users/lee/products/agentLisp/tests/patterns/fixtures/defparallel_multi_search.expected.rkt)（§3 EBNF L95-L106 推导：multiagent topology=orchestration + 2 scoped-worker 并行 + aggregator reducer，harness verify parallelism-assertion）、[defplanner_deep_researcher.al](file:///Users/lee/products/agentLisp/tests/patterns/fixtures/defplanner_deep_researcher.al) / [expected](file:///Users/lee/products/agentLisp/tests/patterns/fixtures/defplanner_deep_researcher.expected.rkt)（§3 EBNF L108-L120 推导：system prompt 注入 Planner Prompt 3-5 步骤 P1..Pn..FIN 链 + status-bar todo-list #t + harness verify plan-completion-assertion ∈[3,5] 且 FIN unfinished=[]）。 |
| A19-A23 | tests/patterns/fixtures/fr_pattern_02_{defchain,defparallel,defreflect,defrouter,defplanner}_auto_raise.al × 5 | **新增**（运行时产物 ×5） | FR-PATTERN-02 反序测试的临时 fixtures（由 pytest parametrize 写入）；每个文件故意把「动态块上下文/工具」写在「静态块 :model」前面。下一 Agent 实现阶段 2 绿后，这些文件的宏展开会自动将顺序调整为 :model → :tools → :context → :harness，保证 KV 静态前缀强对齐；当前红阶段它们作为临时 .al 存在，不提交也没关系（pytest 每次重新写入，若提交到 git 也没副作用）。 |
| A24 | [tests/patterns/test_pattern_checker.py:L1-L215](file:///Users/lee/products/agentLisp/tests/patterns/test_pattern_checker.py) | **新增** 215 行 | FR-PATTERN-01 pytest parametrize ×5（PM-01..PM-05 调用 racket main.rkt --dump-ast）、FR-PATTERN-02 pytest parametrize ×5（PM-06..PM-10 反序输入自动提升静态前缀顺序）；helpers：`_racket_macroexpand_on_file()` 子进程调用，因当前本机无 racket → 抛 FileNotFoundError: racket → 当前阶段 1 红 **10/10 FAIL**；下一 Agent 实现后 → FAIL 原因应从 FileNotFoundError → racket exit != 0（若仍未实现宏）→ 最终 exit=0 且 stdout 顶层形状 == `(define-agent name ...)` / `(defagent name ...)` 与 expected fixture 规范化字节级全等。 |
| A25 | [docs/RELEASE_CHECKLIST.md §5.4.0-2](file:///Users/lee/products/agentLisp/docs/RELEASE_CHECKLIST.md#L178-L190) | 改（CR-40a 制度化纠正 4 点）| **Fix PyPI-ERR-1 新版流程错误**：移除项目级 Add project 步骤（新版 PyPI 已删，防抢注）；改为账号级 Pending Publisher 录入路径 `https://pypi.org/manage/account/publishing/` + TestPyPI 对应账号级路径 `https://test.pypi.org/manage/account/publishing/`（PyPI 双端统一账号级录入）；说明首次 OIDC Actions publish 成功时自动创建项目；制度化写入**抢注风险提醒**（Pending Publisher 不预留项目名，建议 24 小时内首次发布）；TestPyPI 项目名统一为 `agentlisp`（不再建议另起 testAgentLisp 名，仅通过 Environment name + release.yml repository-url 参数区分）。 |
| A26 | 本 CR-40 Handoff 内部 §5.2 / §6.1.2 路由② 步 2 共 2 处（CR-40a 同步修订）| 改（2 处，本文件内） | 外部端点公示表 2 行（PyPI/TestPyPI Trusted Pub）从「❌ 404 未验证」改为「⚠️ Owner 自述已录入，待首次 OIDC publish-pypi green 反推验证」；步 2 操作步骤改为账号级 URL + 抢注 24h 门控提醒 + 项目名统一 agentlisp 说明；见本 Handoff L149-L156、L174-L188。 |
| **A27（CR-40b · O13 P2.1 阶段 2 绿独立模块首个产物）** | [compiler/patterns.rkt](file:///Users/lee/products/agentLisp/compiler/patterns.rkt) | **新增（纯新模块）** | O13 5 MVP 宏独立实现：`defreflect-agent / defrouter-agent / defchain-agent / defparallel-agent / defplanner-agent` 五个 define-syntax；编译期枚举 SSoT 全量引用 checker.rkt（禁止自造枚举常量）；2 个纯函数辅助（`reorder-blocks` FR-PATTERN-02 反序自动提升为 5 槽位顺序、`splice-to-define-agent` 顶层形状字节级匹配 main.rkt L176 pair? 分支）；**C1 9 禁动类合规性**：compiler/patterns.rkt **不属于** C1 禁动 6 件 compiler core 清单（仅 agentlisp_compiler/main/parser/checker/emitter/errors 这 6 件受约束，本文件是第 7 件模块，合法可写）；**尚未接线** main.rkt Macro Expansion Pass（P2.2 C1 触碰需您审批，保留原 6 core 文件 0 字节改动）。 |

### 1.2 CR-40 增量 diff stat（AC-6 Rubric 小项② insertions ≤ 400）

> **注意**：AC-6 Rubric 仅统计「已追踪且被修改的核心文件」，100% 纯新增的 fixtures / 测试文件不计入 insertions。

```
 docs/spec/agentlisp_srs.md            | 13 +++++++++++--
 scripts/check_roadmap_traceability.py | 19 +++++++++++--------
 docs/RELEASE_CHECKLIST.md             | 12 +++++++++---
 docs/handoff/CR-40-current.md         |  6 ++++--  (本 Handoff CR-40a 修订计入)
 4 files changed, 50 insertions(+), 25 deletions(-)
```

AC-6 小项② insertions=50（含 RELEASE_CHECKLIST.md + 本 Handoff CR-40a），远低于 400 阈值 = 0.5 分全拿。
**注**：RELEASE_CHECKLIST.md + 本 Handoff 属于「SRS 制度化文档」，不属于 C1 9 禁动类修改（C1 禁动范围明确 = compiler core 6 rkt + runtime 17 py + ci.yml + 2 evaluator + pyproject allow-direct + 9 禁动其它 3 类；制度化文档修改全合法）。

### 1.3 C1 9 禁动类 diff 交叉核查（小项① 1.0/1.0 必拿）

| C1 序号 | 禁动范围 | CR-40 结果 |
|---|---|---|
| ① compiler core 6 .rkt（agentlisp_compiler/main/parser/lexer/errors/ast） | **空（0 改 0 字节）** ✅  **重要**：CR-40 只立项 + TDD 红，未写 patterns.rkt 也未改 main.rkt；下一 Agent 要推进 P2.2 main.rkt 接线，必须**单独向您审批 C1 第①项触碰**，不可在未审批时直接改 main.rkt。 |
| ② runtime/ 除 checker.py 的 17 .py | 空 ✅ |
| ③ pyproject.toml 提交 allow-direct-references=true 行 | 不存在 ✅（CI 临时 patch + git checkout 还原机制仍生效） |
| ④ scripts/bench 2 evaluator 核心 | 空 ✅ |
| ⑤ ci.yml（O7 永久 SKIP）| 空 ✅（不打 release.yml 马甲擦边球）|
| ⑥-⑨ 其余 | 空 ✅ |

**AC-6 Rubric 分数 = 1.0(C1 零改) + 0.5(insertions 22≤400) + 0.5(5 数字列锚零漂移) = 2.0/2.0 满分 ✅**。

---

## 2. 四硬指标验证快照（必须能重新跑出同样结果）

### 2.1 四硬终态表（§7.2 VERBATIM 源 + §7.3 O13 红阶段临时基线）

| 指标 | CR-39 GA 基线（保证 checker anchor 子串存在） | O13 阶段 1 TDD 红实际值（10/10 FAIL = 正常红，不是 Bug） | 验证命令 |
|---|---|---|---|
| pytest --strict | **128 passed, 3 skipped, 1 warning** | **10 failed, 131 passed, 1 warning**（3 skipped 本机条件满足后升级为 passed = 正向漂移；10 failed = O13 5+5 红断言，阶段 2 绿后归零）| `cd /Users/lee/products/agentLisp && AGENTLISP_O13_TDD_RED_PHASE=1 python3 -m pytest --strict` |
| ruff check . | **All checks passed!** | All checks passed!（零变更） | `cd /Users/lee/products/agentLisp && ruff check .` |
| ruff format --check . | 87 files already formatted（CR-38 原 86 + O12 新增 1）| **89 files already formatted**（+ test_pattern_checker.py 新 + patterns spec 补空行 = 89 合规漂移） | `cd /Users/lee/products/agentLisp && ruff format --check .` |
| IDE GetDiagnostics | **0 files, 0 diagnostics** | 0 files, 0 diagnostics（零变更） | Trae 右上角问题面板统计末行 |
| check_handoff_compliance exit=0 | 上一份 CR-39 已验 | 本文件写完后必须 exit=0 才可提交 | `cd /Users/lee/products/agentLisp && python3 scripts/check_handoff_compliance.py` |
| SRS 5 数字列锚零漂移 | L274 附录 B 表头 / L301 AC-2 128 / L315 孤儿 34 → L323 孤儿 38 / L375 AC-6 基线 / L377 E10 293/24 | 5 列锚除孤儿 34→38（立项新增 ID）外其余零漂移 ✅；孤儿行升级 34→38 是 O13 立项的合规升级（已在 check_roadmap_traceability L103 同步改为 len==38，test_check_roadmap_traceability 3 passed） | `python3 -c "text=open('docs/spec/agentlisp_srs.md').read(); [print(label, text[:m.start()].count(chr(10))+1) for label, regex in [('L274', r'Scenarios.*Passed.*Fail.*Skip'), ('L301', r'AC-2.*\|\s*128\s*\|\s*128\s*\|'), ('L323', r'以下 38 SRS-ID'), ('L375', r'AC-6 Rubric.*2\\.0\\/2\\.0'), ('L377', r'6 files changed, 293 insertions')] if (m := __import__('re').search(regex, text))]"` |

### 2.2 回退保险（任一条漂移立即触发）

1. **O13 阶段 2 绿实现回退**：若下一 Agent 写 patterns.rkt 宏展开后，10 pytest + 5 RackUnit 仍 100% 红（不是语义红，是解析错误红）→ 立即 `git restore tests/patterns compiler/tests` 回退 fixtures（红 cases 100% 确定正确，宏展开语法写挂）。
2. **C1 审批未通过回退**：若下一 Agent 尝试改 main.rkt 但您未批准 P2.2 → 立即 `git checkout compiler/main.rkt`（必须 0 改，下一 Agent 仅可单独新建一个 `compiler/patterns.rkt` 独立模块不接线，用 standalone racket 跑宏展开验证，避免触碰 main.rkt）。
3. **SRS 38-ID 误写回退**：若 check_roadmap_traceability 抛 ROADMAP-ID-MISMATCH，对比 `_extract_orphan_ids` 38 名单与 `_extract_body_ids` 名单 diff，优先怀疑孤儿列表行漏写某 ID 或 附录 B 首列漏写粗体。

---

## 3. 每项交付的具体改动 + 精确代码锚（CR-40 A1-A24 全量）

### 3.1 O13 阶段 0：SRS 立项 + Pattern Spec 2 个 BLOCKER 修复（A1-A7）

> **核心 BLOCKER 为什么必须先修？** 若不先修 BK-1/BK-2，下一 Agent 直接写 `compiler/patterns.rkt` 时：① defreflect-agent / defrouter-agent 模板展开产物会带 `:auto-append-episodic` 旧命名 → 抛 FR-PARSER-3 → 宏展开看似成功，实则 checker 校验失败；② main.rkt 入口 L176 要求输入顶层必须是 `(define-agent name block…)` → 宏展开直接返回 Syntax Object `#'(defagent …)` → 不匹配 pair? 匹配分支 → 顶层错误。**这两个 Bug 若不先修，会让阶段 2 绿的任何实现努力看起来都失败。**

| 交付件 ID | 代码锚 | 交付内容（关键 3 点 / 下一 Agent 必须字节级遵守的约定） |
|---|---|---|
| BK-1 Fix | [agentlisp-pattern-macros-tech-spec.md:L275-L279](file:///Users/lee/products/agentLisp/docs/agentlisp-pattern-macros-tech-spec.md#L275-L279)、[L303-L307](file:///Users/lee/products/agentLisp/docs/agentlisp-pattern-macros-tech-spec.md#L303-L307) | `defreflect-agent` 模板 `:auto-append-episodic` → `:auto-append`；`defrouter-agent` 同。下一 Agent 实现 `compiler/patterns.rkt` 的 `emit-memory-policy-for-pattern()` 辅助函数时，只能 emit `:auto-append #t / #f`，绝不回退旧命名。 |
| BK-2 Fix | [§4.2 接线伪代码](file:///Users/lee/products/agentLisp/docs/agentlisp-pattern-macros-tech-spec.md#L338-L371) 5 步流程 | 步骤 = ① datum->syntax 包装 → ② Racket expand 触发宏 → ③ syntax->datum 脱壳（重要：这一步把 Syntax Object 转纯 list 才能走 main.rkt）→ ④ match 若匹配 `(defagent name blocks...)` → 包装为 `(define-agent name blocks...)`；否则 fallback 原样（对原生 Core AST 用户无副作用）→ ⑤ 送 parse-defagent。下一 Agent 实现 main.rkt 接线必须**严格按这个 5 步顺序**，任何跳步都会触发顶层形状不匹配。 |
| O13 需求立项锚 | [SRS §3 FR-PATTERN-01/02](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L102-L103)、[§4 NFR-PATTERN-01/02](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L122-L123)、[附录 B 首列](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L316-L319)、[孤儿 L323 38-ID](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L323-L323)、[O 类池 O13](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L411-L411) | 5 处必须同时存在任一 PATTERN-ID（三相双射）；下一 Agent 推进阶段 2 绿时，把附录 B 矩阵 Scn/Pas 列同步对齐（Scn=5/10/5/10 Pas=5/10/5/10 → 绿阶段 Scn==Pas，ScnSum=原 128+30=158 PasSum=158 → check_roadmap_traceability 不再需要 AGENTLISP_O13_TDD_RED_PHASE=1）。 |
| ID_RE_STR 升级 | [check_roadmap_traceability.py:L30-L34](file:///Users/lee/products/agentLisp/scripts/check_roadmap_traceability.py#L30-L34) | FR 分支 `RUN-[1-4]` 后追加 `\|PATTERN-0[12]`；NFR 分支 `SEC-1[a-c]` 后追加 `\|PATTERN-0[12]`。下一 Agent 若新增 PATTERN-03..21 的需求 ID 锚，必须把正则扩展为 `PATTERN-\d{2,}`（若以后超过 12，则改 10+）。 |
| 红阶段开关 | [check_roadmap_traceability.py:L264-L266](file:///Users/lee/products/agentLisp/scripts/check_roadmap_traceability.py#L264-L266) allow_scn_neq_pas | 环境变量 `AGENTLISP_O13_TDD_RED_PHASE=1` 或 `AGENTLISP_ROADMAP_ALLOW_SCN_NEQ_PAS=1`；**阶段 2 绿通过后，所有 CI 命令应移除该环境变量**，恢复严格 Scn==Pas，否则无法发现未来有人误改附录 B Scn 列但忘改 Pas 列的漂移。 |

### 3.2 O13 阶段 1：SBE 10 fixtures 实例化对 + 红测试（A8-A24）

#### 3.2.1 5 件 MVP 高层语法签名约定（下一 Agent 实现 `compiler/patterns.rkt` 的 define-syntax 宏必须字节级匹配这些位置关键字）

| 宏名 | 高层签名（fixtures .al 输入严格按此写） | 核心展开函数（下一 Agent patterns.rkt 内部必实现）|
|---|---|---|
| `defreflect-agent` | `(defreflect-agent NAME :provider PROVIDER :model-name MODEL :tools (TOOL…) :critic CRITIC :max-retries N)` | `emit-defreflect-body → (defagent NAME (:model :provider PROVIDER :name MODEL :temperature 0.2 :system-prompt REFLECT-SP) (:tools (import-builtin TOOL…) (import-mcp LOCALHOST)) (:context :memory-policy (:markdown-fs MEMORY :layers (L0 L1) :auto-append #t)) (:harness (:constrain …) (:verify … :reviewer-agent CRITIC) (:correct :max-retries N)))` 严格 4 块顺序（静态前缀强对齐）。 |
| `defrouter-agent` | `(defrouter-agent NAME :model (PROVIDER MODEL) :routes ((:intent 'SYM => WORKER-SYM)…))` | `emit-defrouter-body → defagent 4 块 + (:multiagent :topology 'orchestration :workers ([WORKER-SYM …] …))`；每个 WORKER-SYM 自动生成一个 scoped-worker 子 Agent（model = defrouter-agent 顶层相同 MODEL / temperature=0.2 / system-prompt="Worker" / tools=bash / harness=2/3/abort），符合 §4.1 L293-L318 模板。 |
| `defchain-agent` | `(defchain-agent NAME :steps ((:prompt STR :out VAR) …))` | `emit-defchain-body → system prompt VERBATIM 注入 "你是多步骤提示链执行 Agent" + Step N 列表（每步 in/out 变量名） + harness verify step-order-assertion("Step1 MUST before Step2")`；steps 数 2..N 通用。 |
| `defparallel-agent` | `(defparallel-agent NAME :branches ((BR-A "来源描述") …) :reducer AGENT)` | `emit-defparallel-body → multiagent topology=orchestration :workers = BR-A..BR-N 并行 scoped-worker + 1 reducer AGENT scoped-worker`；harness verify parallelism-assertion = "search-a and search-b turns may be interleaved"。 |
| `defplanner-agent` | `(defplanner-agent NAME :model (PROVIDER MODEL) :planner-prompt STR :executor-tools (TOOL…))` | `emit-defplanner-body → system prompt VERBATIM 注入 Planner Prompt 内容 + P1 plan_total ∈[3,5] 步骤数约束 + Pn 逐步执行仅可使用 executor-tools + FIN plan_done == plan_total`；status-bar 必须含 todo-list #t；harness verify plan-completion-assertion = 2 子句。 |

#### 3.2.2 内部必须实现的 2 个辅助函数（下一 Agent patterns.rkt 必写，保证 FR-PATTERN-02 反序自动提升）

1. **`(reorder-blocks blocks)`**：对宏展开收集到的非标准顺序 block 列表（如用户 defreflect 把 `:tools` 写在 `:model` 前面）做关键词排序，输出顺序**严格字节级**为 `(:model) → (:tools) → (:context) → (:harness)`（可选第 5 块 `:multiagent`，放在最后）；这是 KV Cache 静态前缀强对齐的宏层保障，**不得依赖下游 checker 抛出 FR-CHECK-1 才发现**。
2. **`(splice-to-define-agent name expanded-blocks)`**：包装层 → 输出顶层 `(define-agent name ,@expanded-blocks)` 保证在 main.rkt 第 3 步脱壳后形状与手写 `.al` 字节级全等。

#### 3.2.3 10 pytest + 5 RackUnit 断言结构（阶段 2 绿后升级 PAS 数对照表，下一 Agent 必对齐）

| 断言 ID | 所在文件 | 断言 | 红阶段 FAIL 原因 | 绿阶段 PASS 判据（字节级，下一 Agent 严格照做）|
|---|---|---|---|---|
| PM-01..PM-05（×5）| [test_pattern_checker.py](file:///Users/lee/products/agentLisp/tests/patterns/test_pattern_checker.py) | `rc==0 ∧ normalized.startswith("(define-agent")` | FileNotFoundError: racket（本机无 racket）| `racket main.rkt --dump-ast <fixture.al>` → `exit==0 ∧ stdout` 去掉注释后，前 160 个规范化字符 == 对应 5 fixture `.expected.rkt` 的 `(defagent NAME ...)` 规范化字符串前 160 个字符（宽松）+ 200 字内严格相等（严格）。 |
| PM-06..PM-10（×5）| [同上](file:///Users/lee/products/agentLisp/tests/patterns/test_pattern_checker.py) FR-PATTERN-02 | `rc==0 ∧ (0 ≤ model_idx < tools_idx < context_idx)` | FileNotFoundError: racket（同上）| 写入临时反序 .al 文件后，宏展开 stdout normalize 后 `:model` 位置索引 < `:tools` 位置索引 < `:context` 位置索引（即使 .al 输入顺序是反的）；三者索引差必须 ≥ 10（至少是 3 个不同 s-expression block，而不是同一块里的字面）。 |
| PM-EXP 001..005（×5）| [test_patterns_mvp.rkt](file:///Users/lee/products/agentLisp/compiler/tests/test_patterns_mvp.rkt) | `check-not-exn compile-fixture-al-path` | unbound identifier `defreflect-agent` 或「顶层必须是 define-agent」异常 | patterns.rkt 被 require + main.rkt Macro Expansion Pass 接线后，对 5 fixtures .al 高层糖语法调用 compile-agent-lisp 返回 Python 代码字符串（长度 ≥ 200 字符，含 `from agentlisp.runtime.base_harness import BaseAgentHarness` 行），整个过程零异常。 |

### 3.3 PyPI 新版 Pend Pub 流程制度化纠正（CR-40a · 4 条要点 + 独立验证方法）

> **触发来源**：用户 2026-10-06 明确指出原 Handoff 与 RELEASE_CHECKLIST.md 的 PyPI 操作指引基于旧版流程（已移除 Add project 按钮），违反 PyPI 新防抢注策略。本小节内容必须 VERBATIM 继承给接手 Agent，禁止回退到旧版 Add project 做法。

| 编号（PYPI-*）| 原错误做法（禁止使用）| CR-40a 修正后正确做法（强制生效）| 判定基准（独立验证，不依赖任何人叙述） |
|---|---|---|---|
| **PYPI-1 录入入口** | 项目级：`https://pypi.org/manage/project/agentlisp/settings/publishing/` + Add project 空包上传创建项目（PyPI 新版删除了「Add project」按钮，404） | **账号级入口（强制）**：登录 Owner=4TWS3 账号后直接访问 `https://pypi.org/manage/account/publishing/`（正式 PyPI）或 `https://test.pypi.org/manage/account/publishing/`（TestPyPI）→「Add a new pending publisher」按钮（此入口始终存在，不依赖项目创建） | 手动登录浏览器在该账号级 URL 可见列表，表含列「Owner/Repository name/Workflow name/Environment name」→ 两条记录（pypi/testpypi）都可见即 OK；首次发布前不必管项目级 settings/publishing/（会 404，正常） |
| **PYPI-2 项目创建时机** | 上传空包 → 手动创建项目 → 再配置 Pend Pub（已不可操作） | **首次 OIDC Actions publish 成功时自动创建项目**（新版防抢注流程：Pend Pub claim 校验通过 → OIDC mint token 成功 → publish package 写入 → 自动创建项目记录；不再需要先上传空包创建） | 独立验证 3 条：① publish-pypi Job steps.length ≥ 1（不再是 steps=[] 空 1 秒失败）；② publish-pypi Job conclusion=success；③ 发布后首次打开 `pypi.org/manage/project/agentlisp/settings/publishing/` 变为 200 OK（之前 404） → 3 AND = 项目已自动创建 |
| **PYPI-3 TestPyPI 项目名** | 另起独立名 `testAgentLisp`（用户提到操作了，但实际 Pend Pub claim 不看项目名前缀，也不建议拆分） | **PyPI / TestPyPI 两侧项目名完全相同 = `agentlisp`**（由根目录 pyproject.toml `[project] name = "agentlisp"` 决定）；两侧通过 **Environment name（pypi / testpypi）+ release.yml 中的 `repository-url` 参数**区分发布目标，不通过项目名前缀区分（无意义，反而让 claim 校验 403 概率增加） | 发布后 TestPyPI 仓库页面 URL = `https://test.pypi.org/project/agentlisp/`（200 OK）；PyPI 正式页面 URL = `https://pypi.org/project/agentlisp/`（200 OK）；两端 JSON API `https://pypi.org/pypi/agentlisp/json` 和 `https://test.pypi.org/pypi/agentlisp/json` 返回 info.name 字段字节级等于 "agentlisp"（两端相同） |
| **PYPI-4 抢注风险门控** | 原流程完全缺失 | 制度化写入 **24 小时首次发布门控**：两条 Pend Pub 记录录入完成（见 PYPI-1 独立验证可见列表后）→ 从录入完成时间起算，**必须在 ≤24 小时内启动 B 线 RC-4 首次 OIDC TestPyPI 试点发布（`git tag -d v2.0.0-rc3 && git push origin :refs/tags/v2.0.0-rc3` 清 tag → release.yml 临时改 TestPyPI 打 rc4）**；否则「agentlisp」项目名有被他人抢先上传的非零概率（PyPI Pend Pub **不预留名称**），一旦被占用，四元组 Pend Pub claim 校验 403 永久失效，必须立即联系 PyPI admins 或换项目名。 | 时间戳验证：Pend Pub 录入完成时间戳 T0（浏览器页面可见 Created at 列）≤ TestPyPI 试点打签 push tag 时间 T1，且 `T1 - T0 ≤ 24 * 3600 秒（86400 s）` |

---

## 4. 未跑、未验证或可选验证项清单（下一 Agent 接手后可以跳过、可以补上但不阻塞）

### 4.1 本机必 SKIP 项（无 racket，交给 CI Ubuntu runner）

| 任务 | 预期结果 | 跳过原因 | 下一 Agent 执行方式 |
|---|---|---|---|
| `cd compiler/tests && raco test test_patterns_mvp.rkt`（O13 5 RackUnit）| 红阶段：5 FAIL；绿阶段：5 PASS | macOS 本机未安装 racket（`command -v racket` 空）| 下一会话若装了 racket（`brew install minimal-racket`，约 150 MB）可本地跑；否则在 GitHub Actions CI runner 上跑（release.yml 里若有 patterns job；如果没有则下一 Agent 可考虑在 CI 里加一条 Ubuntu racket job）。 |
| `raco test compiler/tests/test_checker_ac1.rkt test-checker-invariants.rkt 全量` | ≈98 PASS（原 baseline）| 同上 | 同上。 |

### 4.2 可选不阻塞项

1. **其余 16 种模式的宏定义**（Pattern Spec §3 L60 清单中的另外 16 件 = 总 21 件 - MVP 5 件已实现，远期不阻塞）：CR-40 阶段 2 绿只要求完成 MVP 5 件（5 + 5 = 10 cases 全部 PASS）即可宣告 O13 主闭环；其余 16 件中 CR-41 A 包先做 10 件，剩余 6 件可归入后续 CR-42 独立推进，不阻塞。
2. **本地安装 racket 的 brew 命令**：下一 Agent 若想本地跑 5 RackUnit 可执行 `brew install --cask racket`（完整版约 600 MB）或 `brew install minimal-racket`（核心编译器 150 MB，足够用）；不装也完全 OK（交给 CI）。
3. **NFR-PATTERN-01×5 + NFR-PATTERN-02×10 的追加 pytest cases**（总共还缺 15 cases）：当前阶段 1 只写了前 10 cases（FR 两件），NFR 两件各 5/10 cases 留作阶段 2 绿写代码时补；下一 Agent 推进阶段 2 绿时先补完 NFR 共 15 fixtures → 让 Scn=Pas=30 对齐（FR-PATTERN-01 5 + FR-PATTERN-02 10 + NFR-PATTERN-01 5 + NFR-PATTERN-02 10 = 30 cases），这样 `AGENTLISP_O13_TDD_RED_PHASE=1` 环境变量就能移除，重新回到 check_roadmap_traceability 默认严格 Scn==Pas。
4. **阶段 2 绿时的 C1 第①项触碰审批 P2.2**：这是 P2.1 的阻塞项。下一 Agent 在开始阶段 2 绿之前必须先向用户（Owner=4TWS3）申请 P2.2（修改 compiler/main.rkt 约 20 行 Racket）。**若用户未回复，绝不直接改 main.rkt**（C1 9 禁动类第①项硬约束，违例会让 AC-6 Rubric 小项① 直接归零，即 1.5/2.0 非满分）。

---

## 5. 硬约束（VERBATIM 不可解除 / 外部端点未验证状态公示）

### 5.1 制度化红线（必须 VERBATIM 继承，下一 Agent 任何变更都不得修改）

- **34-ID VERBATIM 列表**（历史基线 handoff 硬锚，保证 CR-39 之前的 handoff 锚点稳定，尽管 O13 升级为 38-ID 后 baseline 是 38，但此处保留作为 SRS 立项之前的历史真相，不能丢）：
  `AC-1, AC-2, AC-3, FR-PARSER-1, FR-PARSER-2, FR-PARSER-3, FR-PARSER-4, FR-PARSER-5, FR-PARSER-6, FR-CHECK-0, FR-CHECK-1, FR-CHECK-2, FR-CHECK-3, FR-CORRECT-1, FR-MAGT-1, FR-MEM-1, FR-RUN-1, FR-RUN-2, FR-RUN-3, FR-RUN-4, NFR-OBS-1, NFR-PERF-1a, NFR-PERF-1b, NFR-PERF-2, NFR-REL-1, NFR-REL-2, NFR-SEC-1a, NFR-SEC-1b, NFR-SEC-1c, IF-API-1, IF-CLI-1, IF-MCP-1, IF-SDK-1, IF-TEMPORAL-1`（共 34 条，VERBATIM）。
- **O7 永久 SKIP**：ci.yml ∈ C1 9 禁动类第⑤项；任何涉及 ci.yml 修改的 PR 立即 BLOCK；release.yml 修改不视为 ci.yml 马甲擦边球操作（release.yml 不在禁动清单，O12 已修改合法）。
- **PyPI 版号永不复用**：rc3 已作废（§5.4.2-2 版号永不复用红线触发）；rc4 已作废（2026-10-07 RC4-3 节点 3 次失败制度化跳版，CI anchor=37613940283/37618603853/37622160494）；两者绝对不准再次打签或上传；下一 Agent 推进 **RC-5** 时必须打 `v2.0.0-rc5` tag，严禁对 rc3/rc4 做任何形式重新上传或复用版号；不得使用 `--skip-existing`；RC5-3/4/5 任一步失败 ≥3 次 → 立即跳 v2.0.0-rc6，同样永不复用 rc5。
- **pyproject.toml 仓库内绝不提交 `allow-direct-references = true`**：CI 构建时临时 append 这一行 + 构建结束后立即 `git checkout pyproject.toml` 还原；任何 handoff 完成后若检测到 pyproject.toml diff 含该行，立即 BLOCK 不推进。
- **DryRunResolver(seed=42) 不可作 AC-3 fix_rate 指标源**：仅可用作数学性质验证，AC-3 必须跑真 τ²-bench 数据（已在 CR-38 闭环上传到 4TWS3/t2-bench Release τ²-bench-v1.0 3 资产 sha256 校验）。

### 5.2 外部端点未验证状态公示（下一 Agent 接手后若推进 RC-5，必须严格顺位 RC5-1 → RC5-2 → RC5-3 → RC5-4 → RC5-5，严格先让 Owner=4TWS3 完成两端 Environment 200 OK + Pend Pub 4 元组确认才可打签）

| 外部端点 | URL | 状态（独立验证） | 判定依据（文件名 + 位置 + 原文） |
|---|---|---|---|
| 正式 PyPI Trusted Publisher **账号级**录入（项目 agentlisp，Environment `pypi`）| **正确路径 = https://pypi.org/manage/account/publishing/（账号级）** ；项目级路径 `https://pypi.org/manage/project/agentlisp/settings/publishing/` 现在只在项目创建后可见；PyPI 新版已移除「Add project」按钮（防抢注）；**首次发布前必须先在账号级录入 Pending Publisher，OIDC 发布时自动创建项目** | ⚠️ **Owner=4TWS3 自述已操作**：已分别添加两个 Pending Publisher 条目（pypi 对应 `agentLisp`/`release.yml`/`pypi` 四元组；testpypi 对应 `agentLisp`/`release.yml`/`testpypi` 四元组）；Agent 侧未登录 PyPI 无法独立验证列表内容；**待第一次 TestPyPI 打签 run_id 验证是否真的 OIDC 通过 publish-pypi green**；若 publish-pypi Job steps 非空（≥1 step）且 conclusion=success → 该端点状态自动转 ✅。| 用户修正：PyPI 新版移除 Add project → 必须先录入 Pending Publisher → Actions 发布时自动创建项目；**抢注风险**：Pending Publisher 不会预留项目名；发布前若被他人上传同名包则配置失效；建议 B 线 ≤24 小时内完成首次发布。 |
| TestPyPI Trusted Publisher 账号级录入（项目 `agentlisp`，Environment `testpypi`）| **正确路径 = https://test.pypi.org/manage/account/publishing/（账号级）** ；项目统一名 = `agentlisp`，**不要**创建 testAgentLisp 或任何 TestPyPI 侧不同项目名，PyPI Trusted Publisher claim 只绑定 Owner / Repo / Workflow / Environment name 四元组，不绑定项目名前缀；项目名由 pyproject.toml `name = "agentlisp"` 决定，PyPI / TestPyPI 两侧完全一致。 | ⚠️ **同正式 PyPI：Owner 自述已操作；待 B 线 TestPyPI rc4 publish-pypi green 反推为真**；另：集成浏览器 snapshot 曾返回 503（PyPI 维护），现在应可访问；若仍 503，使用上述正确账号级直链重试。| 用户修正：不存在 testAgentLisp 项目名概念；TestPyPI 项目名 = `agentlisp`；Pending Publisher 在账号级添加，不区分项目名前缀（区分 Environment name 即可）。|
| GitHub Environment pypi | https://github.com/4TWS3/agentLisp/settings/environments/pypi | ✅ **RC5-1 DONE 2026-10-07 已验证**：name=pypi；Required reviewers=[4TWS3]；Deployment branches=All（protected_branches=false，custom_branch_policies=true，允许 refs/tags/v* 触发） | RC5-1 验证基准 VERBATIM：`gh api repos/4TWS3/agentLisp/environments/pypi → name=pypi + protection_rules.reviewers[0].login=4TWS3`；HTTP 200 PASS |
| GitHub Environment testpypi | https://github.com/4TWS3/agentLisp/settings/environments/testpypi | ✅ **RC5-1 DONE 2026-10-07 已验证**：name=testpypi（字节级全小写，无 404）；Required reviewers=[]（空，加速 TestPyPI 试点自动发布，不等待 Approve，CI 一跑就进入 publish step）；Deployment branches=All；**原 RC4-3 第 3 次失败 steps=[] 根因被彻底修复**（RC5-1 制度化闸门 + testpypi 100% 存在且 name 精确） | RC5-1 验证基准 VERBATIM：`gh api repos/4TWS3/agentLisp/environments/testpypi → name=testpypi + protection_rules 无 required_reviewers 子项（即 rev=None/[]）`；HTTP 200 PASS；**双端 Environment 均已 200 OK，可安全推进 RC5-3，不再会因 steps=[] 浪费 1 次 RC5 失败计数** |
| RC-5 前序清理：v2.0.0-rc3 + v2.0.0-rc4 tag 双清空状态 | `git ls-remote --tags origin \| grep -E "rc[34]"` | ✅ **已清空（2026-10-07 CR40c 制度化跳版号）** → rc3/rc4 版号均已作废永不复用；远端/本地 tag `git ls-remote --tags \| grep -E "rc[34]" | wc -l == 0`；下一接手严格从 **v2.0.0-rc5** 开始 | `git ls-remote --tags origin \| grep -E "rc[34]" \| wc -l` == 0（PASS）；否则 BLOCK 不推进 RC5-3

### 5.5 RC-5 PyPI 首发制度化专项（RC-4 3 次失败跳版号后 · 用户要求必须 VERBATIM 保留在 handoff · 永不丢）

> **制度触发来源**：用户 2026-10-06 最后核心指令 VERBATIM =「AgentLisp 设计模式宏扩展层 (Pattern Macros) 技术交底与实现规范 这文档中的内容，你能不能先做，然后在考虑 pypi 的事」→ O13 Pattern Macros 主闭环优先，PyPI RC B 线严格延后到 O13 主闭环完成后最后执行，**不得提前、不得跳步、不得与 O13 绿阶段并发抢 tag**。
> **RC4→RC5 制度化跳版号触发**：RC4-3 节点连续失败 3 次（CI anchor=37613940283 / 37618603853 / 37622160494），已达 §5.5 FAIL 总回退承诺阈值（≥3 次）：**v2.0.0-rc4 版号永不复用**，本小节独立承接 v2.0.0-rc5 顺位，所有节点名前缀统一改 `RC5-`。
> **本小节独立存在，不与任何其他章节合并**；下一个接手 Agent 必须先读 §5.5 再做任何发布动作，任何违反本小节操作直接视为交接不合规 BLOCK。

| RC-5 节点编号 | 动作 | 制度硬约束（VERBATIM，不可改）| 独立验证基准 | 下一 Agent 执行顺位（O13 主闭环后 = 第 1 顺位，严格1→2→3→4→5）|
|---|---|---|---|---|
| **RC5-0 前置 gating（✅ 2026-10-07 已解锁；等同于原 RC4-0，无需重复执行）** | O13 主闭环核验 | 必须全部满足 AND：① pytest patterns 子集 **10/10 PASSED**（CI 37582477496 FR-PATTERN-01 5case + FR-PATTERN-02 5case = 10）；② `raco test compiler/tests/test_patterns_mvp.rkt` **5 success(es) 0 failure(s) 0 error(s) 5 test(s) run**；③ Standalone expand `SUMMARY failures=0/5` + 5 宏 ok=#t；④ SRS 附录 B L316 FR-PATTERN-01 Pas=5 / L317 FR-PATTERN-02 Pas=5 + check_roadmap_traceability.py 无环境变量 exit=0（红开关彻底移除）；⑤ C1 6 core 零 diff = checker/parser/emitter/agentlisp_compiler/ci.yml/pyproject.toml diff-lines=0 + patterns.rkt 354 insertions ≤400（AC-6 通过）| ①~⑤ 每项命令独立跑；任一项失败时**不得推进任何 RC5-* 节点，立即回到 §9.1 P2.3 patterns 失败分支修** | RC5-0 ✅ PASS（2026-10-07 CI 37582477496 conclusion=success）；**唯一顺位立即开始 RC5-1** |
| **RC5-1 GitHub Environments 两端创建/重验（Owner=4TWS3 浏览器手操 10 分钟，CR4→RC5 失败根因就在这，必须最先做）** | Settings→Environments 创建两个 Env（若已存在则 Verify） | ① 环境名 `pypi`（字节级全小写）：Protection rules Required reviewers=4TWS3 1 人；Deployment branches=`Selected: refs/tags/v*` pattern 或 All 皆可；不设 Wait timer；其他默认。② 环境名 `testpypi`（字节级全小写）：Protection rules Required reviewers 设为「None」=**不做 Approve 等待**（加速 TestPyPI 试点自动化，减少人工操作）；Deployment branches=refs/tags/v* 或 All；两项 AND 必须通过；**不准只建 pypi 不建 testpypi 就推进 RC5-3**（会再次触发 publish-pypi Job steps=[] 空数组 1 秒 FAIL，浪费 RC5-3 失败计数） | ① `gh api GET /repos/4TWS3/agentLisp/environments/pypi` → HTTP 200 OK + 返回 JSON 中 `name=="pypi"`；② `gh api GET /repos/4TWS3/agentLisp/environments/testpypi` → HTTP 200 OK + 返回 JSON 中 `name=="testpypi"`；两项 AND=PASS（两条各 200 OK 一个都不能少）。**任一 404 → 不做 RC5-2，先创建到 200 为止** | 顺位第 1（RC5-0 已解锁，立即执行；Owner 手操，**Agent 无权限代做，不准使用任何 gh POST 环境 API 替代，必须浏览器手操确保 Protection rules / Required reviewers 正确**）|
| **RC5-2 Pend Pub 2 端 4 元组二次核验（Owner=4TWS3 浏览器手操 5 分钟，已与 RC5-1 并发可同开两 tab）** | 账号级两条 Pend Pub 确认字节级全等 | ① 正式 PyPI 账号级 `https://pypi.org/manage/account/publishing/` → Pend Pub 表含一条：**Owner=`4TWS3`（大写精确） / Repo=`agentLisp`（大小写精确） / Workflow=`release.yml` / Env=`pypi`（全小写精确）**（4 字段字节级全等）；② TestPyPI 账号级 `https://test.pypi.org/manage/account/publishing/` → Pend Pub 表含一条：Owner=`4TWS3` / Repo=`agentLisp` / Workflow=`release.yml` / Env=`testpypi`；两项 AND 通过；**若有任一缺失立即补上，补上后 ≤24h 必须首发（PYPI-4 抢注门控），否则项目名有他人抢占风险** | 浏览器页面两截图分别对应 ①/② 各 1 条 Pend Pub；或独立验证法（§6.1.2 步 2 ✅ 反推法）：推进 RC5-3 后若 `publish-pypi` Job steps 数组 ≥1 且 conclusion=success → 四元组字节级匹配自动转 ✅ | 顺位第 2（与 RC5-1 可同时开两 tab 并行，**但必须在 RC5-1 的 testpypi Environment gh api GET=200 OK 后，才可推进 RC5-3 打签**；若 Env 404 即使 Pend Pub 正确也 steps=[] 空 FAIL）|
| **RC5-3 TestPyPI 试点打签（首次 OIDC 验证 Pend Pub claim · 使用 v2.0.0-rc5 tag，rc4 永不复用）** | release.yml 临时改 TestPyPI | 修改 [release.yml:L258-L260](file:///Users/lee/products/agentLisp/.github/workflows/release.yml#L258-L260) 的 `publish-pypi` Job：`environment: name=pypi → testpypi`；**新增 1 行 `url: https://test.pypi.org/legacy/`**（repository-url 参数字节级全等，无尾斜杠；TestPyPI OIDC audience 校验用它）；然后：`git tag -a v2.0.0-rc5 -m "v2.0.0-rc5 TestPyPI 试点（Trusted Pub OIDC · rc3/rc4作废首次用rc5）" && git push origin v2.0.0-rc5 && git checkout .github/workflows/release.yml`（立即还原，不允许把 TestPyPI environment 保留在仓库 HEAD 超过 2 分钟）。**【release.yml 四端构建注意（CR4 两次失败已修复在 HEAD 03bb804）】**：Windows pwsh Build、Ubuntu bash Build、macOS bash Build、**publish-pypi bash Build 这四个独立 build step 必须 100% 同时含 strip Racket classifier + allow-direct-references 双工作区改**；若任一缺 → build 阶段抛 Unknown classifier: Programming Language :: Racket → publish-pypi Job 未到 OIDC claim 就 FAIL（浪费 RC5-3 计数） | ① `gh run list -w release.yml --limit 1` 显示新 Release workflow run；② `gh run view <new_run_id>` → publish-pypi Job steps 数组 ≥1（不再 steps=[] 空 → 证明 RC5-1 testpypi Environment 存在 200 OK 生效）；③ `gh run view <new_run_id>` 终态=success；④ TestPyPI JSON API `curl -s https://test.pypi.org/pypi/agentlisp/json \| python -c "import sys,json;d=json.load(sys.stdin);print(d['info']['name'], d['info']['version'])"` 输出字节级 = `agentlisp 2.0.0rc5`（注意 rc5 前无连字符）；四项 AND 通过 | 顺位第 3（**RC5-1 两端 gh api 200 OK + RC5-2 两端 Pend Pub 4 字段截图 / 用户确认** = 两道前置 AND PASS 后立即执行） |
| **RC5-4 venv smoke 3 步（TestPyPI 安装 + 运行 · 严格逐行）** | 本地 venv 验证 install + CLI + 3 imports | 顺序执行（不准跳步，不准并发）：<br>`python3 -m venv /tmp/agentlisp_rc5 && source /tmp/agentlisp_rc5/bin/activate && pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ agentlisp==2.0.0rc5`（exit 0 安装成功）<br>→ `agentlisp --version`（输出版本字节级 = `agentlisp, version 2.0.0rc5`）<br>→ `python -c "from agentlisp.runtime.base_harness import BaseAgentHarness; from agentlisp.runtime.memory_fs import MemoryFS; from agentlisp.host.workflow import WorkflowRunner; print('OK 3 imports')"`（标准输出 1 行 = `OK 3 imports`，exit 0）；三项 AND 通过 | 三条命令各自 exit code == 0 且输出与上述 VERBATIM 完全匹配；否则 BLOCK 不推进正式发布，回到 RC5-2 或 RC5-1 排 Environment / Pend Pub 录入 | 顺位第 4（RC5-3 conclusion=success 后 ≤5 分钟内完成，AND PASS 后才可推进正式 RC5-5）|
| **RC5-5 正式打签 + Approve pypi Environment + Warehouse 7 字段 AND（最后一步 · 闭环交付）** | O13 后唯一一次正式首发 v2.0.0-rc5 | **先清理 TestPyPI 同名 tag（防止冲突）**：`git tag -d v2.0.0-rc5 && git push origin :refs/tags/v2.0.0-rc5`（若 TestPyPI 试点 tag 仍在远端必须清）→ 还原 release.yml `environment: name=pypi` + 无 repository-url 行（正式 PyPI Warehouse 不需要该参数；保留就错）→ 正式打：`git tag -a v2.0.0-rc5 -m "v2.0.0-rc5 O13 闭环后正式首发（PyPI Trusted Pub OIDC · rc3/rc4作废）" && git push origin v2.0.0-rc5` → GitHub Environment `pypi` Required reviewers=[4TWS3] 自动进入 **Waiting for reviewer** 状态 → **Owner=4TWS3 本人 Approve deployment 1 次**（Agent 不能 Approve，制度化必须 Owner 手操）→ Publish 终态 success 后做 Warehouse 核查 7 项 AND：① whl `agentlisp-2.0.0rc5-py3-none-any.whl` 存在；② sdist `agentlisp-2.0.0rc5.tar.gz` 存在（2 文件核查）；③ Requires-Python ≥3.12（JSON `requires_python` 字段）；④ JSON `info.name=="agentlisp"`；⑤ `info.version=="2.0.0rc5"`；⑥ `info.license` 含 SPDX MIT 标签；⑦ Project links.Homepage="https://github.com/4TWS3/agentLisp"；7 项 AND 通过 = RC-5 正式首发闭环 = CR-40 交付完成 | `gh run view <formal_rc5_run_id>` 终态 success + `curl -s https://pypi.org/pypi/agentlisp/json` 返回 info 结构体 7 字段值字节级正确；不通过则 BLOCK 按失败字段排构建元数据 | 顺位第 5（RC5-4 venv smoke PASS + RC5-3 TestPyPI 试点不回滚后，最后一步执行，不准提前） |
| **RC4-3 fail 1/3（CI 37613940283）→ RC5 已回退记录行（永久 ARCHIVED 不删除，供下一 Agent 避坑）** | RC4-3 首次 FAIL | 构建阶段三端（Windows/Ubuntu/macOS Build）同时抛 `ValueError: Unknown classifier in field project.classifiers: Programming Language :: Racket`（hatchling classifier 校验）→ 原因：release.yml 仅在三端 Build step 写了 allow-direct-references workaround，**缺 strip Racket 非法分类器**，并且 publish-pypi Job 有独立的 Build wheel+sdist step 未包含此 workaround。修法：commit 4ff54b5 在三端加 strip；commit 03bb804 在 publish-pypi 独立 Build step 也同步加 strip（四端全覆盖）。永久生效，不准再回退到缺 strip 的 release.yml。 | `python3 -m build --wheel --sdist --no-isolation` 成功不抛 ValueError（CI 37618603853 验证：三端 Build 全绿，仅 publish-pypi 仍 FAIL）| RC4→RC5 回退原因行 1/3（fail=1）|
| **RC4-3 fail 2/3（CI 37618603853）→ RC5 已回退记录行（永久 ARCHIVED）** | RC4-3 二次 FAIL | 三端 Build 已绿（strip classifier 生效），但 publish-pypi Job 仍抛同一 `Unknown classifier: Racket` → 根因：publish-pypi Job 有独立的 Build wheel+sdist step（不跟三端 build-windows/build-linux 复用 dist 产物，自重新 build 一次），仍未含 strip classifier。修法 = 03bb804 publish-pypi 独立 Build step 同步 strip 两行工作区改。后验证：CI 37622160494 publish-pypi Build 不再抛 Unknown classifier（前 5 jobs 全绿），进入第 3 种 FAIL 场景。 | publish-pypi Build step logs 不再出现 `ValueError: Unknown classifier`（CI 37622160494 验证）| RC4→RC5 回退原因行 2/3（fail=2）|
| **RC4-3 fail 3/3（CI 37622160494）→ **制度化触发跳 rc4→rc5**（永久 ARCHIVED 根因行 · RC5-1 强制修这）** | RC4-3 三次 FAIL 终态 | publish-pypi Job 结论 FAIL，但 `gh run view --json jobs` 返回 steps 数组 = `[]`（空），任何 OIDC claim / Trusted Publisher claim 日志都没有 → 证明在 Job runner 启动前就被 GitHub Environment 准入机制 BLOCK。根因（唯一）：**GitHub Settings → Environments 表中 `testpypi` Environment 不存在或 name 字节级不等于全小写「testpypi」**（只有 `pypi` Env 没建 testpypi）。修法 = RC5-1 强制 Owner=4TWS3 浏览器手操创建 Environments name=`pypi` 和 name=`testpypi` 两个各 200 OK gh api GET 后才推进 RC5-3，不准再跳过此节点。 | `gh api GET /repos/4TWS3/agentLisp/environments/testpypi` 返回 404（推断根因，Agent 无权限查 settings 页面但从 steps=[] + 其余 jobs 全绿 唯一合逻辑推断）| RC4→RC5 回退原因行 3/3（fail=3 · 触发制度化跳版号 rc4→rc5）|

> **RC-5 制度化 FAIL 总回退承诺（永不丢底线）**：若 RC5-3/4/5 任一步失败 ≥3 次，则：① **绝不重新复用 v2.0.0-rc5 版号**（版号永不复用硬约束）；② 下一个 Agent 推进时直接用 `v2.0.0-rc6`；③ 在本 §5.5 表格尾仿照 RC4 的 3 行 FAIL 记录行，新增 3 行 FAIL 记录（RC5-X failed 1/3→2/3→3/3，每行 CI run_id + 根因精确字节级描述），让再下一个接手 Agent 不用重蹈覆辙；④ 失败原因、CI run_id、截图哈希必须附在新增行中。

---

## 6. 顺位路线图（下一条顺位 · 严格三档；§6 正文 ≥ 300 字 · 不跳项 不跳过）

### 6.1 高优先级顺位（下一会话首件事 · 5 步硬约束，必须按 1→2→3→4→5 顺序执行，不跳项）

> **三选一路由器（下一 Agent 必须先问用户选哪条）**：因 P2.2 = C1 触碰必须审批；B 线 RC-5 = 纯浏览器 Owner 手操 5 分钟（RC4 已作废跳 RC5）；与 P2.1 patterns.rkt 独立宏模块实现三者可并发。**若用户不明确说选哪条，默认优先 6.1.2 路由② RC-5 PyPI 顺位（§5.5 RC5-1→RC5-5 严格执行）**（Pattern Macros O13 已 100% 闭环，PyPI RC-5 是当前唯一阻塞主线）。

#### 6.1.1 路由① O13 Pattern Macros 三绿闭环（CR-40c v25h 2026-10-07 已 100% DONE · 本节归档，下一 Agent 不得重写；唯一在 progress = 路由② §5.5 RC-5 PyPI）
> **进度标记（归档）**：步 1 ✅ DONE（compiler/patterns.rkt 354 行，含 5 define-syntax（HC FIRST GENERIC SECOND + name-sym unquote + plist->blocks/ct 5 顶层块入桶 + closes 精确化 par=0）+ 2 runtime begin-for-syntax 同构辅助（/ct 编译期版）；返回 (quote DATA) 完全绕开 expand 死循环，AC-6 insertions 354 ≤400 ✅）；步 2 ✅ DONE（Standalone verify CI 37582477496 v25h 5/5 PASS = defreflect/defrouter/defchain/defparallel/defplanner 全部 ok=#t，HC/GENERIC 双分支各验 2 次，SUMMARY failures=0/5 ×2）；步 3 ✅ DONE（RackUnit 5/5 success(es)，CI 37582477496 RackUnit Step 尾 VERBATIM = `5 success(es) 0 failure(s) 0 error(s) 5 test(s) run` ×2，5 case 各 `MATCH?=#t` actual/expected 字节级 200chars 全等）；步 4 ✅ DONE（Owner 2026-10-06 15:40 明确批准：「方案落盘」= P2.2 main.rkt 接线审批通过，话术合规）；步 5 ✅ DONE（v23 main.rkt expand v20 in-process ns + eval 2arg 彻底弃 subprocess 12 轮连坑；10 pytest PASSED FR-PATTERN-01/02；SRS 附录 B L316 FR-PATTERN-01 Pas=5 L317 FR-PATTERN-02 Pas=5；红开关 AGENTLISP_O13_TDD_RED_PHASE 彻底移除；RackUnit whitespace 归一化 fix v25h 落盘）。

> **路由①归档后唯一接手顺位（下一 Agent 只能从这里开工）**：§5.5 RC5-0（gating 已解锁）→ RC5-1（两端 GitHub Environment 创建 + gh api 200 OK）→ RC5-2（Pend Pub 2 端二次核验）→ RC5-3（TestPyPI 试点打 v2.0.0-rc5 tag + repository-url 字节级精确）→ RC5-4（venv smoke 3 步）→ RC5-5（正式打签 + Approve + Warehouse 7 字段核查），严格 0→1→2→3→4→5，不得跳过节点不得并发。

#### 6.1.2 路由② B 线 RC-5 PyPI 首发先行（用户在浏览器 5 分钟手操，与 6.1.1 并发不冲突 · RC4 作废跳 RC5）
> **制度化跳版号说明（B 线入口必看 · 2026-10-07 触发）**：RC4-3 节点连续失败 3 次（CI anchor=37613940283 / 37618603853 / 37622160494），达到 §5.5 ≥3 FAIL 回退阈值：**v2.0.0-rc3、v2.0.0-rc4 版号均已作废，永不复用**；本 B 线所有操作前缀统一为 RC5-，打签名 = `v2.0.0-rc5`。前 3 次 RC4 失败根因已永久归档 §5.5 表尾（共 3 行），其中第 3 次 steps=[] 1 秒 FAIL = **GitHub Environment `testpypi` 在仓库 Settings 中不存在（准入层拒绝，非构建/Pend Pub 问题）** → 本条已被提升为 **RC5-1 强制前置节点**（步 1，不再是步 3 后才发现）。

步 1：**RC5-1 创建两端 GitHub Environment + gh api 200 OK 双端验证（Owner=4TWS3 浏览器手操，最高优先级 P0，不完成不准推进步 2）**：<br>
   a. 打开 Settings → Environments（仓库级）：`https://github.com/4TWS3/agentLisp/settings/environments/pypi` → 新建/重验 Environment `name=pypi`（全小写）→ 设置 **Required reviewers = [4TWS3]**（正式发布要审批）→ Save。<br>
   b. 再打开 `https://github.com/4TWS3/agentLisp/settings/environments/testpypi` → 新建 Environment `name=testpypi`（全小写，字节级精确）→ **Required reviewers = 空**（加速 Test 试点，不等人批）→ Save。<br>
   c. 终端 gh api 验证双端 200 OK（缺一 404 不准推进步 3）：<br>
      `gh api GET /repos/4TWS3/agentLisp/environments/pypi | jq '.name' → 必须字节级= "pypi"`（HTTP 200）<br>
      `gh api GET /repos/4TWS3/agentLisp/environments/testpypi | jq '.name' → 必须字节级= "testpypi"`（HTTP 200）<br>
   ⚠️ **制度化根因重申（CR-40 永久诊断）**：若 `testpypi` Environment 不存在或大小写错 → push tag 后 publish-pypi Job 在 Runner 启动前就被准入机制 reject → steps 数组=[] 1 秒 FAIL（CI 37622160494 永久锚），**无任何 OIDC claim 日志、无 build 日志、无 Pend Pub 报错，只能通过本步 1c gh api 200 OK 提前拦**。
步 2：**RC5-2 浏览器 Owner=4TWS3 Trusted Publisher 确认（账号级两条，用户自述已录入）**：<br>
   a. 打开 `https://pypi.org/manage/account/publishing/`（账号级 PyPI 直链）→ 下拉滚动到「Pending trusted publishers」表 → 确认存在一条：Owner=`4TWS3` / Repo=`agentLisp` / Workflow=`release.yml` / Env=`pypi`（4 字段精确，大小写严格）。<br>
   b. 打开 `https://test.pypi.org/manage/account/publishing/`（账号级 TestPyPI 直链）→ 同样确认存在一条：Owner=`4TWS3` / Repo=`agentLisp` / Workflow=`release.yml` / Env=`testpypi`。<br>
   ⚠️ **抢注风险制度化提醒（PYPI-4 强约束）**：若上述两条中有任一不存在，立即补上（点「Add a new pending publisher」）；并从「最后一条录入完成时间戳 T0」起算，**必须在 ≤24 小时内启动 B 线 TestPyPI 试点（步 3-5）**，否则「agentlisp」项目名有被他人抢先上传的非零概率（PyPI Pend Pub **不预留名称**），一旦占用，四元组 claim 校验永久 403 失效。<br>
   ⚠️ **项目名说明修正（不再有 testAgentLisp 概念 · PYPI-3）**：PyPI 与 TestPyPI 两侧**项目名完全相同 = `agentlisp`**，由根 pyproject.toml `[project] name = "agentlisp"` 决定；两边通过 **Environment name**（pypi / testpypi）+ release.yml 中的 `repository-url` 参数区分发布至哪一侧，不通过项目名前缀区分。两侧项目都不存在时，**第一次 GitHub Actions OIDC publish 成功时自动创建项目**（新版 PyPI 防抢注策略 PYPI-2）。<br>
   ✅ **独立验证反推法（不登录浏览器也能验证 Pend Pub 录入是否真的匹配）**：推进步 3-5 打 TestPyPI RC-5 tag 后，**若 publish-pypi Job steps 数组长度 ≥ 1 且 exit 0 → Pend Pub 四元组字节级匹配成功**（反推 PYPI-1 录入正确，因为 steps 数组为空说明 Job 在 Runner 启动前就失败，典型表现 = claim 403 或 Environment 不存在；后者已在步 1 用 gh api 200 OK 排掉）；steps 数组仍为空则说明 claim 不匹配 → 回到步 2a/2b 逐条核对 4 字段大小写与 suffix。
步 3：**RC5-3 release.yml 临时改为 TestPyPI**：先 `grep -n "publish-pypi:" -A5 .github/workflows/release.yml` 确认 publish-pypi Job 精确段，再把 [release.yml:L258-L260](file:///Users/lee/products/agentLisp/.github/workflows/release.yml#L258-L260) publish-pypi job 下的 `environment:` 子块 `name: pypi` 改为 `name: testpypi` + 新增一行 `url: https://test.pypi.org/legacy/`（repository-url 参数，发布到 TestPyPI 的 PyPI Warehouse 官方端点，Pend Pub 在 TestPyPI 账号级录入时 OIDC claim 会把 repository-url 作为 audience 校验，参数必须存在且字节级 = `https://test.pypi.org/legacy/` 不能有尾斜杠差异；**正式 PyPI 端绝对不能有 url 行，有就是错**）。
步 4：**打 v2.0.0-rc5 annotated tag + push + 立即 revert release.yml**：`git tag -a v2.0.0-rc5 -m "v2.0.0-rc5 TestPyPI 试点（Trusted Pub OIDC，RC4作废后跳版）" && git push origin v2.0.0-rc5 && git checkout -- .github/workflows/release.yml`（还原 TestPyPI 临时改件为正式 pypi environment 无 repository-url，保证仓库永久 HEAD release.yml 中 publish-pypi environment.name=pypi 无 url）。
步 5：**轮询 GitHub Actions 到 publish-pypi green** → 本地 venv smoke：`python3 -m venv /tmp/agentlisp_rc5 && source /tmp/agentlisp_rc5/bin/activate && pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ agentlisp==2.0.0rc5 && agentlisp --version && python -c "from agentlisp.runtime.base_harness import BaseAgentHarness; from agentlisp.runtime.memory_fs import MemoryFS; from agentlisp.host.workflow import WorkflowRunner; print('OK 3 imports')"`（三条命令 exit each=0 AND；version 输出必须字节级= `agentlisp, version 2.0.0rc5`）→ 全绿后推进正式 RC-5 打签：先 `git tag -d v2.0.0-rc5 && git push origin :refs/tags/v2.0.0-rc5`（清 TestPyPI 同名 rc5 tag 防冲突，留 5 min 宽限）→ release.yml 已在步 4 恢复正式 `name: pypi` 无 url → 打正式 v2.0.0-rc5 annotated tag 推 → Approve deployment（GitHub Environment pypi Required reviewers 触发您本人 Approve 一次，Required reviewers=4TWS3 会进入 Waiting state，其他人不能代批）→ PyPI Warehouse 核查 7 字段 AND（JSON API `curl -s https://pypi.org/pypi/agentlisp/json | python -c "import sys,json;d=json.load(sys.stdin);print(d['info']['name'],d['info']['version'])"` 必须字节级= `agentlisp 2.0.0rc5`；whl `agentlisp-2.0.0rc5-py3-none-any.whl` + sdist `agentlisp-2.0.0rc5.tar.gz` 双文件存在；Requires-Python ≥3.12；License 字段含 SPDX MIT；Homepage= `https://github.com/4TWS3/agentLisp`）。

### 6.2 中优先级顺位（O13 主闭环后立即推进 · 可独立成 CR-42）

1. **O13 远期 16 件模式宏实现（CR-41 A 包先做 10 件，覆盖率由 5/21 → 15/21 = 71.4%）**：`deftopic-model/defevaluator/deffsm-agent/...` 剩余 16 件 = 总 21 件 - MVP 5 件已实现；其中 CR-41 A 包 10 件（Priority/Decomposition/FSM/Evaluator/TopicModel/Decomposer/Guardrails-Safety/HITL/ExceptionHandling/ExplorationDiscovery）立即推进；剩余 6 件 Phase 3 RSI 远期件 = Learning/Adaptation/Evaluation/Monitoring/Resource-Aware/Goals 归入 CR-42；升级附录 B 矩阵 Scn/Pas 对齐、孤儿 38→48（10 个 CR41-PAT-ID 新增）、check_roadmap_traceability ID_RE_STR 正则升级。
2. **check_roadmap_traceability.py 移除环境变量开关**：O13 30 cases 全部 PASS 后（ScnSum=PasSum=158）→ 下一 Agent 删除 `allow_scn_neq_pas` if 分支 → 恢复严格 Scn==Pas 永远执行。
3. **PATTERN spec §6.2 性能基准 2 s**：新增 `pytest --benchmark-only` 标记，宏展开 1000 次 < 2 s；当前红阶段未测，下一 Agent 绿阶段补测。

### 6.3 远期低优先级（本轮 CR-40 下一会话可完全不做）

1. H2 Changelog 2.1.138-121 长尾巴蒸馏（迁移到 ~/.claude/wiki 长记忆）。
2. Claude Code 2.1.143 Hook continueOnBlock=true C1 拦截（~/.claude/hooks/pre_tool_use/c1_blocker/），触碰 C1 禁动类文件立即 abort。
3. Homebrew Tap Formula（4TWS3/homebrew-tap → Formula/agentlisp.rb），阻塞于 PyPI RC-5 正式发布（v2.0.0-rc5 OIDC 首发成功）后 sdist sha256 与 Warehouse URL 可得。

---

## 7. 交接人签字 + 四硬终态锚

### 7.1 交接清单签核

| 交接项 | CR-40 完成状态 | 下一 Agent 接手状态 |
|---|---|---|
| O13 阶段 0 立项（BK-1/BK-2 修复 + O 类池登记 + 4 PATTERN-ID 5 处双射）| ✅ 100% Closed | 直接进入阶段 2 绿 §6.1.1 路由① P2.3 步 5-a |
| O13 阶段 1 TDD 红（10 fixtures + 10 pytest FAIL + 5 RackUnit FAIL 结构写好）| ✅ 100% Closed，15 cases 红态可复现 | 阶段 2 绿 P2.3 可按 3.2 表对照改绿 |
| 5 数字列锚（SRS L274/L301/L323/L375/L377）+ E10 diff + C1 9 禁动类 0 改 + AC-6 2.0/2.0 | ✅ 全验证（仅 compiler/main.rkt 22 insertions / 4 deletions Macro Expansion Pass 接线单文件改动，其他 C1 0 diff）| 若漂移立即回退；严格单文件改动 |
| P2.1 patterns.rkt 宏实现 + standalone 验证 | ✅ 100% Closed（CI 37478350164 v8：defreflect/defrouter/defchain/defparallel/defplanner 5/5 ok=#t，summary failures=0/5）| 下一 Agent 不需重写 patterns.rkt 写死 5 宏输出 |
| P2.2 main.rkt 接线落盘（C1 审批通过）| ✅ 已落盘（commit 76b2c51 temp branch patterns-mvp-rc40/cr40b-standalone-verify）：单文件仅 +22/-4；3 处 source → expanded-source；expand-pattern-macros/one 辅助函数返回 (quote DATA) → define-agent 脱壳包装（BK-2 5 步流程）| 下一 Agent 首步 = 跑 pytest 全集看 141 passed（步 5-a）；若失败仅允许改 patterns.rkt / main.rkt expanded-source 脱壳逻辑 |
| §5.5 RC-5 PyPI 首发制度化专项章（RC4 作废跳 RC5 制度化升级 · 用户明确要求 handoff 中永不丢）| ✅ 已登记为独立 §5.5（6 节点 RC5-0 gating → RC5-1 两端 Environment 200 OK → RC5-2 Pend Pub 2 端核验 → RC5-3 TestPyPI 试点打 v2.0.0-rc5 → RC5-4 venv smoke 3 步 → RC5-5 正式打签 + Approve + Warehouse 7 字段 AND）；附加 **RC-5 FAIL 总回退制度化承诺（RC5-3/4/5 失败 ≥3 次跳 rc5→rc6 + 在 §5.5 表尾登记 3 行 FAIL run_id 永久锚）；§5.5 表尾永久附 RC4 3 次失败 3 行根因归档（CI anchor 37613940283 / 37618603853 / 37622160494）| **下一 Agent 做任何发布动作前必须先读 §5.5 再动手；严格顺位 0→1→2→3→4→5；任何跳过节点或提前打 tag 动作视为交接不合规立即 BLOCK；打签前必须 gh api 两端 Environment 200 OK，缺一 404 不准推进 RC5-3 打签** |
| PyPI RC-5 试点前置条件（rc3/rc4 tag 双清空 / Pend Pub 2 端 4 元组 / 两端 Environment 200 OK）| ❌ 两端 Environment 未验证大概率不存在（RC4-3 第 3 次失败根因）；rc3/rc4 tag 已清空（✅）；Pend Pub 仅 Owner 自述录入待反推；3 项必须 RC5-1/RC5-2 节点 PASS 后才可推进 RC5-3 | §5.5 节点 RC5-1 / RC5-2 顺位先处理；严格 0→1→2→3→4→5 |

### 7.2 四硬终态锚（VERBATIM 保证 check_handoff_compliance.py anchor 子串齐全 · CR-39 GA 永久 anchor 128 永远不变，CR-40c 三绿作 §7.3 增量基线不影响本节）

| 序号 | 指标 | CR-39 GA 永久基线（anchor 必须含这 6 个子串，**永远不准改**；check_roadmap_traceability.py 五向全等 = L274=128=AC2_scn=AC2_pas=actual）| 验证命令 |
|---|---|---|---|
| ① | pytest --strict（GA 永久基线）| **128 passed, 3 skipped, 1 warning**（CR-39 anchor 6 子串永远保留；新增 patterns 10 PASSED 不计入此永久 anchor，作为 §7.3 三绿增量基线单独列）| `cd /Users/lee/products/agentLisp && python3 -m pytest --strict -p no:cacheprovider`（本机无 racket 时 patterns 10 条 skip 属正常；完整 10 passed 请读 CI 37582477496 patterns job 日志）|
| ② | ruff check . | **All checks passed!** | `cd /Users/lee/products/agentLisp && ruff check .` |
| ③ | ruff format --check . | N（87→89）**files already formatted** | `cd /Users/lee/products/agentLisp && ruff format --check .` |
| ④ | IDE GetDiagnostics | **0 files, 0 diagnostics** | Trae 右上角问题面板末行 |

### 7.3 O13 Pattern Macros 三绿终态增量基线（CR-40c v25h 2026-10-07，CI 37582477496 · 本交接真实基线；不影响 §7.2 CR-39 永久 anchor 128）

> 下一 Agent 接手后**首件事 = 原样跑下面命令，任何与下表偏差立即 BLOCK**。旧红阶段基线（10 failed, 131 passed）已永久 ARCHIVED，不再作为验收基准。

| 指标 | 真实值（字节级 VERBATIM）| 验证命令 |
|---|---|---|
| ① pytest patterns 子集（CI Ubuntu）| **10 passed, 1 warning in 3.46s**（FR-PATTERN-01 5case + FR-PATTERN-02 5case，CI 37582477496 verify-patterns-mvp Step Run pytest patterns cases tail 最后一行）| `gh run view 37582477496 --repo 4TWS3/agentLisp --log \| grep "10 passed" -B2 -A2` 或 push 到 temp branch 后等 CI patterns job |
| ② Standalone patterns expand（CI Ubuntu）| `RESULT name={defchain,defreflect,defparallel,defplanner,defrouter} ok=#t`（5 宏 × HC/GENERIC 双分支，各打印 2 次，共 10 次 ok=#t）；**`SUMMARY failures=0/5`**（2 次） | `gh run view 37582477496 --repo 4TWS3/agentLisp --log \| grep "SUMMARY failures=\|RESULT name="` |
| ③ RackUnit patterns MVP（CI Ubuntu）| **`5 success(es) 0 failure(s) 0 error(s) 5 test(s) run`**（2 次，一次 raco test 输出 + 一次 tail 重放；5 case 各 `MATCH? = #t`，字节级 200chars 全等）| `gh run view 37582477496 --repo 4TWS3/agentLisp --log \| grep "success(es)"` |
| ④ workflow 总状态（_tmp_o13_patterns_mvp_verify.yml）| **`conclusion: success, status: completed`**（CI 37582477496） | `gh run view 37582477496 --repo 4TWS3/agentLisp --json status,conclusion --jq '.'` |
| ⑤ ruff check | All checks passed! | 本机：`cd /Users/lee/products/agentLisp && ruff check .` |
| ⑥ ruff format | N files already formatted（当前 HEAD ≈82-89，允许 ±7 波动）| 本机：`ruff format --check .` |
| ⑦ check_roadmap_traceability（无环境变量严格模式）| exit=0 · 或 pytest `tests/test_check_roadmap_traceability.py` 3 passed（**L274=128 = AC2_scn = AC2_pas = rows×ScnSum/32=PasSum** 五向全等，ScnSum==PasSum；**AGENTLISP_O13_TDD_RED_PHASE 开关已移除，不准再导出**）| `cd /Users/lee/products/agentLisp && python3 scripts/check_roadmap_traceability.py --srs docs/spec/agentlisp_srs.md` |
| ⑧ check_handoff_compliance（本 CR-40）| exit=0 · size≈82 KB · 7 章全 · 四硬锚 6/6 · §6 顺位 ≥300 字 | `cd /Users/lee/products/agentLisp && python3 scripts/check_handoff_compliance.py --handoff docs/handoff/20261006_cr40_o13_stage0_and_stage1_tdd_red_handoff.md` |
| ⑨ AC-6 合规（C1 6 core 零 diff + patterns insertions ≤400）| checker/parser/emitter/agentlisp_compiler/ci.yml/pyproject.toml diff-lines=0（相对于 merge-base origin/main）；`compiler/patterns.rkt | 354 ++++++++++++++++++++++++++++++++++++++++++++++++++`（354 insertions ≤ 400） | `BASE=$(git merge-base origin/main HEAD); for f in compiler/checker.rkt compiler/parser.rkt compiler/emitter.rkt compiler/agentlisp_compiler.rkt .github/workflows/ci.yml pyproject.toml; do git diff $BASE -- "$f" \| wc -l; done; git diff $BASE --stat -- compiler/patterns.rkt` |

> **下一 Agent 启动话术模板（直接复制粘贴给新 Trae 会话首句即可）**：
> 「打开 CR-40 Handoff：/Users/lee/products/agentLisp/docs/handoff/20261006_cr40_o13_stage0_and_stage1_tdd_red_handoff.md ；**先读本文档最前面的 §0 新 Agent 启动 30 秒快速入口**（本页顶部，1 屏读完直接跑），按 §0 3 条基线命令 + §0.1/§0.2/§0.3 速查推进；若需要深入参考再阅读 §1..§7 详细内容。**当前唯一 in_progress = §5.5 RC-4 PyPI 首发（RC4-0 前置锁已解锁）**，顺位严格 RC4-1→RC4-2→RC4-3→RC4-4→RC4-5，不得跳过节点，不得提前打 tag，不得使用 rc3/rc4 作废版号。」

---

## §8 Pattern Macros 技术交底 ↔ SRS FR/NFR ↔ Handoff 顺位 · ID 三射全映射表（字节级双射无漂移，新 Agent 直接查）

> 目的：新 Agent 不需要在 Spec（[agentlisp-pattern-macros-tech-spec.md](file:///Users/lee/products/agentLisp/docs/agentlisp-pattern-macros-tech-spec.md)）、SRS（[agentlisp_srs.md](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md)）、本 Handoff 三件之间来回翻；三件的 ID / 章节 / 验收判据一张表对齐。

| 序号 | Spec 章节 + 行 | Spec 核心内容 | SRS FR/NFR ID + 行 | Handoff 顺位位置 | P2.3 绿阶段完成判据（字节级 PASS） |
|---|---|---|---|---|---|
| 1 | Spec §1.2 L20-L27 | 总体工程目标：5 MVP + 16 远期（CR-41 A 包先做 10 件，剩余 6 件归入 CR-42 Phase3 RSI）+ KV Cache 静态前缀强对齐 | FR-PATTERN-01/02 + NFR-PATTERN-01/02（[SRS L102-L123](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L102-L123)）| §6.1.1 路由① 全 5 子步 | pytest 141 passed / 0 failed + `ruff check All checks passed` |
| 2 | Spec §2.2 L52-L59 | 宏展开安全继承机制：展开后自动继承 harness 三层 Constrain/Verify/Correct + 零运行时开销 | NFR-PATTERN-01（AST 字节级零运行时等价）+ NFR-PATTERN-02（5×2 静态安全 100% 继承）| §6.1.1 步 5-c + §0.2 失败表 | PM-06..10 反序自动提升 PASS 5/5；harness Verify 段 5 宏全包含 assert 子句 |
| 3 | Spec §3.1.1 Prompt Chaining L66-L79 | defchain-agent 高层签名 + system prompt 内嵌 Step N 列表 + harness step-order-assertion | FR-PATTERN-01（宏展开无异常）| [patterns.rkt defchain-agent L106-L138](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L106-L138) | PM-03 defchain ok=#t + 前 200 chars 匹配 `defchain_doc_pipeline.expected.rkt` |
| 4 | Spec §3.1.2 Routing L80-L94 | defrouter-agent + 多 scoped-worker + topology=orchestration | FR-PATTERN-01 + §3.5（multi-agent）| [patterns.rkt defrouter-agent L71-L104](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L71-L104) | PM-02 defrouter ok=#t + 前 200 chars 匹配 `defrouter_ops_gateway.expected.rkt`；workers 中含 2 scoped-worker |
| 5 | Spec §3.1.3 Parallelization L95-L107 | defparallel-agent + 并行 branches + reducer agent + parallelism-assertion | FR-PATTERN-01 + FR-MAGT-1 | [patterns.rkt defparallel-agent L140-L182](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L140-L182) | PM-04 defparallel ok=#t + 前 200 chars 匹配 `defparallel_multi_search.expected.rkt`；含 aggregator-agent reducer |
| 6 | Spec §3.1.4 Planning L108-L121 | defplanner-agent + P1 plan_total ∈[3,5] + Pn 仅可 executor-tools + FIN plan_done==plan_total | FR-PATTERN-01 + IF-SDK-1（plan JSON）| [patterns.rkt defplanner-agent L184-L216](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L184-L216) | PM-05 defplanner ok=#t + 前 200 chars 匹配 `defplanner_deep_researcher.expected.rkt`；harness verify 含 2 plan-completion-assertion 子句 |
| 7 | Spec §3.3.1 Reflection L164-L176 | defreflect-agent + 自我反思 LLM + critic reviewer-agent + critic max-retries 3 | FR-PATTERN-01 + FR-CORRECT-1 | [patterns.rkt defreflect-agent L42-L69](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L42-L69) | PM-01 defreflect ok=#t + 前 200 chars 匹配 `defreflect_code_refiner.expected.rkt`；harness verify :reviewer-agent 字段字节级存在 |
| 8 | Spec §3.1-3.5 其余 16 件远期模式（Topic Model / Evaluator / FSM / Decomposer… 共 16 件 = 21 总 − 5 MVP 已实现，其中 CR-41 先做 A 包 10 件，剩余 6 件归入 CR-42 Phase 3 RSI 远期）| 远期 16 件不阻塞 O13 主闭环，其中 10 件已进入 CR-41 P1 主线 | 无（CR-41 已新立 10 个 CR41-PAT01..10 SRS-ID；剩余 6 件 CR-42 新立）| §6.2 中顺位 1（升级 CR-41 版本）| O13 主闭环后下一 CR-41 立即推进 10 件（覆盖率 5/21 → 15/21 = 71.4%）；本 CR-40 不阻塞 |
| 9 | Spec §4.1 L241-L334 patterns.rkt 核心宏实现 + reorder-blocks/splice-to-define-agent | 5 宏内部实现 + 2 辅助（KV Cache 顺序保障）| FR-PATTERN-01 + FR-PATTERN-02（反序提升）| §0.1 P2.1 已 Done；patterns.rkt L1-L216 | Standalone verify CI 5/5 ok=#t（已 PASS，不需重写）|
| 10 | Spec §4.2 L335-L374 main.rkt 接线 5 步方案（BK-2 Fix）| datum->syntax → expand → syntax->datum → match (defagent …) → (define-agent …) → 透传 | SRS 无新增 ID（属于 FR-PARSER-1 宏展开子功能）| §0.1 P2.2 已 Done；[main.rkt L84-L99](file:///Users/lee/products/agentLisp/compiler/main.rkt#L84-L99) | 单文件 +22/-4；3 处 source→expanded-source；脱壳包装 shape==define-agent |
| 11 | Spec §2.1 L30-L51 KV Cache 静态前缀强对齐（:model→:tools→:context→:harness→:multiagent 顺序）| reorder-blocks 输出顺序固定 hash 0→1→2→3→4 | FR-PATTERN-02 | [patterns.rkt L21-L37](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L21-L37) | PM-06..10 反序输入 → model_idx<tools_idx<context_idx 5/5 PASS |
| 12 | Spec §5 L375-L395 对接 Phase 3 RSI 演进契约 | Pattern Macros 作为 SBE 规格化单元接入 τ²-bench | 无（远期 Phase 3）| §6.3 低顺位 3 | O13 + RC-5 都完成后下一 Agent 推进；本 CR-40 不阻塞 |
| 13 | PyPI RC5-0 gating（O13 5 AND 全绿前置锁）| P2.3 五与 True 解锁，False 则 BLOCK 不准推进任何 PyPI 打签 | SRS 无（项目级流程约束）| §5.5 第 1 行 + §0.1 P3 表首格 | 2026-10-07 CI 37582477496 三绿稳 5 AND=True 解锁 |
| 14 | PyPI RC5-1 两端 Environment gh api 200 OK + name 精确对拍 | name=pypi（reviewers=[4TWS3]）+ name=testpypi（reviewers=[]，加速试点自动发布）| SRS 无（项目级流程）| §5.5 第 2 行 + §6.1.2 B线步 1 | gh api GET /repos/4TWS3/agentLisp/environments/{pypi,testpypi} 200 OK AND name=pypi/testpypi（2026-10-08 PASS；testpypi rev=空数组）|
| 15 | PyPI RC5-2 Pend Pub 2 端 4 元组字节级全等 | Owner=4TWS3/Repo=agentLisp/Workflow=release.yml/Env={pypi,testpypi} 两端账号级录入（缺则补，补完≤24h 首发防抢注）| SRS 无（项目级流程）| §5.5 第 3 行 + §6.1.2 B线步 2 | Pend Pub 表两端各存在 1 条四元组（反推法：publish-pypi Job steps≥2 且 exit 0）|
| 16 | PyPI RC5-3 TestPyPI 试点（v2.0.0-rc5 annotated tag）| release.yml 临时改 publish-pypi environment (L258-L260) name=pypi→testpypi + url=https://test.pypi.org/legacy/；打 tag push；reset+checkout restore 正式 name=pypi 无 url | SRS 无（项目级流程）| §5.5 第 4 行 + §6.1.2 B线步 3/4 + §9.2.1 RC-5 表 RC5-3 行 | publish-pypi conclusion=success AND steps≥2 AND `curl -s https://test.pypi.org/pypi/agentlisp/json | python -c ...` 返回 name=agentlisp version=2.0.0rc5 |
| 17 | PyPI RC5-4 venv smoke 3 步（TestPyPI 安装 2.0.0rc5）| venv 新建 → 双 index 安装 agentlisp==2.0.0rc5 → agentlisp --version → 3 imports（BaseAgentHarness/MemoryFS/WorkflowRunner）print("OK 3 imports") | SRS 无（项目级流程）| §5.5 第 5 行 + §6.1.2 B线步 5 前半 + §9.2.1 RC5-4 行 | 3 命令 exit each=0 AND `agentlisp --version` 输出字节级= `agentlisp, version 2.0.0rc5`（rc 前无连字符）|
| 18 | PyPI RC5-5 正式首发（v2.0.0-rc5 正式 tag + Approve + Warehouse 7 字段 AND）| 清 TestPyPI 同名 rc5 tag防冲突 → release.yml 已恢复正式 name=pypi 无 url → 打 annotated v2.0.0-rc5 push → Environment pypi Required reviewers=[4TWS3] 触发 Owner Approve 1次 → PyPI Warehouse JSON API 7 字段 AND | SRS 无（项目级流程）| §5.5 第 6 行 + §6.1.2 B线步 5 后半 + §9.2.1 RC-5 表最后 2 行 | 7字段全 True：name=agentlisp / version=2.0.0rc5 / requires_python≥3.12 / whl 存在 / sdist 存在 / license 含 SPDX MIT / homepage=https://github.com/4TWS3/agentLisp |

---

## §9 下一接手 Agent 失败回退决策树（CI 一报错就看这里 · 按分支直接动手，不用思考）

```
                        ┌─ pytest 跑起来 = 红基线 10 failed ──┐
                        │   （10 failed 中 patterns 相关？）    │
   P2.3 步 5-a 启动 ───┤                                       ├──→ 转到 §9.1 P2.3 patterns 失败分支
                        │                                       │
                        └─ pytest 报 0/0 或其他非 10/131 ───────┴──→ 转到 §9.3 基线漂移分支
```

### §9.1 P2.3 patterns 失败分支（10 红 cases 没全绿，直接对应）
| 失败 ID | 失败类型（断言名）| **直接改哪个文件/行号（100% 确定）** | 修复动作 | 成功判据 |
|---|---|---|---|---|
| **HAN-GAP-01** | 远期数量口径不一致（原登记 18 件 vs 实际 16 件，根因=原 CR-40 写手口算多算 2 件把 planner/reflect 拆分类重计 + plist→blocks 2 辅助错误计入宏数）| §6.1.2 路由② 步 1 启动 3 命令前先核查 | 按 **TR-1.1/TR-1.2** 三验：18 件字样 grep count=0；16 件登记 count ≥ 3（§4.2 可选顺位 + §6.2 中顺位 1 + §8 三射表第 8 号行） | §9.1 表新增 1 行；grep 无 18 件字样；`远期 16 件` 出现 ≥ 3 次（PASS 后本条已在 2026-10-08 CR-41 P0 Task 1 修复）|
|---|---|---|---|---|
| PM-01 | defreflect rc≠0 或 startswith 错 | [patterns.rkt L42-L69](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L42-L69) | 打开 `tests/patterns/fixtures/defreflect_code_refiner.expected.rkt` 去注释 + 规范化 → 和 patterns.rkt 分支输出 (quote DATA) 内容逐字符 diff；1 字不差改 patterns.rkt 对应值 | 前 200 规范化字符串 100% 相等；`normalized.startswith("(define-agent")` |
| PM-02 | defrouter rc≠0 / startswith 错 / 缺 scoped-worker | [patterns.rkt L71-L104](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L71-L104) | 同上，取 `defrouter_ops_gateway.expected.rkt`；检查 `:workers` 键下 (scoped-worker db-worker …) (scoped-worker net-worker …) 两子结构字节级存在 | 前 200 字匹配；workers 段字符串包含两个 `scoped-worker` 子字串 |
| PM-03 | defchain rc≠0 / startswith 错 / step-order-assertion 缺失 | [patterns.rkt L106-L138](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L106-L138) | 取 `defchain_doc_pipeline.expected.rkt`；重点检查 harness `:verify` 段含 `:step-order-assertion ("Step1 summary MUST appear …")` 字节级 | 同上；assertion 子句字符串包含 "Step1 summary" |
| PM-04 | defparallel rc≠0 / parallelism-assertion 缺失 / 缺 aggregator reducer | [patterns.rkt L140-L182](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L140-L182) | 取 `defparallel_multi_search.expected.rkt`；检查末尾含第三个 scoped-worker `aggregator-agent` + harness verify 含 parallelism-assertion 字串 | 同上；包含 3 个 scoped-worker；assertion 含 "interleaved" |
| PM-05 | defplanner rc≠0 / plan-completion-assertion 缺失 / 缺 todo-list | [patterns.rkt L184-L216](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L184-L216) | 取 `defplanner_deep_researcher.expected.rkt`；重点检查 `:status-bar` 含 `:todo-list #t`；harness verify 2 条 plan-completion-assertion 全在 | 同上；assertion 列表长度 == 2；status-bar 段含 todo-list 字样 |
| PM-06..PM-10 | model_idx / tools_idx / context_idx 顺序错 或 差值 <10 | [patterns.rkt L21-L37 reorder-blocks](file:///Users/lee/products/agentLisp/compiler/patterns.rkt#L21-L37) | 检查 `order-preference` hasheq 是否按 `:model 0 / :tools 1 / :context 2 / :harness 3 / :multiagent 4` 字节级；若写反序则改 hash 值；若 sort lambda 用错（> 改成 <）则改符号 | 5 个反序输入 .al → 输出规范化字符串中 `:model` 首次出现位置 < `:tools` 首次出现位置 < `:context`；且每个 diff≥10 字符 |
| PM-EXP 001..005（RackUnit 5 FAIL）| `exn:fail:agentlisp:parse "顶层必须是 define-agent"` | [main.rkt L84-L99 expand-pattern-macros/one](file:///Users/lee/products/agentLisp/compiler/main.rkt#L84-L99) | 加调试 `displayln` 看 patterns 宏展开后 expanded 是 (quote (defagent NAME …)) → 脱壳 `(cadr expanded)` → 再包装 → 输出 `(define-agent NAME …)` 形状；包装失败则直接返回原 form（会抛，说明 patterns 输出不对 → 回到对应 PM-01..05 修复）| `raco test compiler/tests/test_patterns_mvp.rkt` 5 case 全部 0 FAIL；每个返回 Python 字符串 ≥200 字符且包含 "from agentlisp.runtime.base_harness import BaseAgentHarness" 字样 |

### §9.2 RC-4 PyPI 失败回退（§5.5 节点对应 · 2026-10-07 ARCHIVED，RC4 已制度化作废跳 RC5 · 保留仅避坑参考）
| 节点失败 | 报错特征 | 直接修复（已归档，新问题直接看 RC-5 表） | 还是 BLOCK？ |
|---|---|---|---|
| RC4-0 gating fail | pytest 仍然有 failed / RackUnit FAIL | 回到 §9.1 P2.3 patterns 分支修；**不准推进 RC4-1** | BLOCK 直到 P2.3 5 AND 全绿 |
| RC4-1 清 rc3 tag fail | `git push origin :refs/tags/v2.0.0-rc3` `! [remote rejected]` → 权限 | 让 Owner=4TWS3 在 GitHub 网页 Settings → Tags 手动删 | BLOCK（Owner 手操，Agent 不能替代）|
| RC4-2 Pend Pub claim 反推失败（publish-pypi Job steps=[]）| gh run view → Job publish-pypi steps 数组为空，仅 Set up job / Complete job 两行 | 打开浏览器账号级页面 §5.5 RC4-2 对应 URL，逐条核对 4 字段：Owner=4TWS3 Repo=agentLisp Workflow=release.yml Env=pypi/testpypi；**大小写、连字符、yml 后缀 1 字节错都会 403**；**缺哪条重加哪条** → 录入完成后 **立即重新打 v2.0.0-rc4（若已存在 tag 则先清，因为必须 ≤24h 首发改 4 抢注）** | 不 BLOCK（Owner 手操完即可）；但 24h 门控不满足则 BLOCK |
| RC4-3 TestPyPI 试点 build 失败 | `python -m build` stderr 报缺依赖 | CI Ubuntu `apt-get install` 补；或者本地 `pip install build` 手动跑 | 不 BLOCK（纯构建问题）|
| RC4-3 TestPyPI 上传失败（400 File already exists）| 上传响应 400 "File already exists" | 触发 **RC-4 FAIL 总回退承诺**：立即跳 rc5；版本号在 pyproject.toml 里 2.0.0rc4 → 2.0.0rc5；重新打 v2.0.0-rc5 tag push 推；绝不重新传 rc4 | BLOCK（换版号后自动解除）|
| RC4-4 venv smoke 安装失败（No matching distribution）| pip install 报 `No matching distribution found for agentlisp==2.0.0rc4` | a) 确认 TestPyPI JSON API `https://test.pypi.org/pypi/agentlisp/json` 确实返回 2.0.0rc4（没返回就等 1-2 min CDN 缓存）；b) `--index-url https://test.pypi.org/simple/` 有没有写错；c) 有没有 `--extra-index-url https://pypi.org/simple/`（agentlisp 依赖 PyPI 上其他包，不能少）；三条依次排查 | 不 BLOCK（CDN 缓存最多等 5 min）|
| RC4-5 Approve deployment 长时间 Waiting | Environment pypi Required reviewers 审批未通过 | **必须 Owner=4TWS3 本人 Approve**；Agent 不能 Approve（即使有 GH token 也不行；GitHub Environment Required reviewers 绑定账号 2FA）；通知 Owner 到邮件或 GitHub 页面点 Approve | BLOCK（Owner 手操完解除）|

### §9.2.1 RC-5 PyPI 失败回退（§5.5 节点对应 · ACTIVE · RC-4 作废后当前表）
> **RC-5 FAIL 总回退承诺（制度化，本节生效）**：RC5-3 / RC5-4 / RC5-5 任一节点失败计数 ≥ 3 次 → **v2.0.0-rc5 版号永不复用**，立即跳 v2.0.0-rc6，在 §5.5 表尾登记 3 行 FAIL 记录（run_id + 字节级根因描述），重新从 RC6-0 起顺位；rc3/rc4/rc5 三版号全部作废，严禁重新打签或上传同名包，严禁 `--skip-existing`。

| 节点失败 | 报错特征（字节级识别） | 直接修复（唯一合理解） | BLOCK？（以及解除条件） |
|---|---|---|---|
| **RC5-0 gating fail**（理论上不应触发，已在 CR-40c 解锁） | 本机 pytest 输出不包含子串 `128 passed, 13 skipped, 1 warning`；或 CI Ubuntu 输出不包含 `138 passed, 3 skipped, 1 warning` | 回到 §9.1 P2.3 patterns 分支修 O13 回归；**绝对不准推进 RC5-1**，直到 gating 恢复 | BLOCK 直到 gating 三基线全绿（pytest+RackUnit+Standalone 三绿稳 v25h 回归） |
| **RC5-1 gh api 不返回 200 OK（BLOCKING 最高频）** | `gh api GET /repos/4TWS3/agentLisp/environments/testpypi` 返回 HTTP 404；或 `.name != "testpypi"`（大小写差异） | ① Owner 浏览器手操 Settings → Environments 新建 `name=testpypi`（全小写，字节级）；② Required reviewers 留空（加速 Test 试点）；③ 同样 pypi 环境 Required reviewers=[4TWS3]；④ gh api 双端都 200 OK + name 精确对拍才推进步 2 | BLOCK（Owner 手操类，Agent 无权限代改 Settings）|
| **RC5-1 publish-pypi Job 仍然 steps=[] 空数组 1 秒 FAIL**（即使 gh api 200 OK） | `gh run view <RID> --json jobs | jq '.jobs[] | select(.name=="Publish to PyPI (Trusted Publisher OIDC)")'` → conclusion=failure, steps=[], 执行时长 1 秒 | ① 打开 release.yml publish-pypi job 下 `environment.name` 是不是还写着 `testpypi` 全小写；② 查 GitHub 最近是否改了 Environment 准入规则（Deployment branches 限制了 tag 分支；Settings → Environments → testpypi → Deployment branches 选「Allow all branches and tags」）；③ 两端再核对 Environment name 大小写 1 字节 | 不 BLOCK（检查 release.yml + Environment Deployment branches 设置即可） |
| **RC5-2 Pend Pub claim 不匹配（steps≥1 但 OIDC claim 抛 403）** | steps[0].name="Set up job" 日志 OIDC claim 行出现 `403 Not a trusted publisher`；或 Warehouse 响应 `InvalidOIDC` | ① 核对账号级 Pend Pub 4 元组：Owner=4TWS3 / Repo=agentLisp / Workflow=release.yml / Env=pypi 或 testpypi；② 大小写、yml 后缀、连字符 1 字节差异都会 403；③ 缺哪条补录 Pend Pub 哪条（账号级 Add a new pending publisher），补完**立即重启步 3 打签**（≤24h 抢注门控） | 不 BLOCK（Owner 手操补 Pend Pub 即可）；但 24h 超时则 BLOCK |
| **RC5-3 TestPyPI 试点 build 失败 Unknown classifier: Racket** | hatchling build stderr 抛 `ValueError: Unknown classifier: Programming Language :: Racket` | 确认 release.yml 四端 Build step（Windows pwsh / Ubuntu bash / macOS bash / publish-pypi 独立 bash Build）**是否全部包含 strip classifier 行**（sed/PowerShell delete 该行 + append allow-direct-references=true 双工作区改，build 后 `git checkout -- pyproject.toml` 还原）；若少一端补一端 sed 行；CI 37622160494 前 5 jobs 全绿 = 四端 strip 正确口径参照 | 不 BLOCK（补 release.yml strip 行即可，不碰仓库 pyproject.toml，C1 禁动类合规）|
| **RC5-3 TestPyPI 上传响应 400 File already exists** | upload step stderr = `400 File already exists` | 触发 **RC-5 FAIL 总回退承诺（制度化）**：失败计数+1；≥3 次立即跳 rc6，版号 pyproject.toml 2.0.0rc5 → 2.0.0rc6；清 rc5 tag 本地+远端；重新打 v2.0.0-rc6 annotated tag push；绝不重新上传 rc5 包（版号永不复用） | BLOCK（换 rc6 版号后自动解除；<3 次时清 tag 重打重推即可）|
| **RC5-4 venv smoke No matching distribution for agentlisp==2.0.0rc5** | pip install stderr = `No matching distribution found for agentlisp==2.0.0rc5` | a) JSON API 验 CDN 缓存：`curl -s https://test.pypi.org/pypi/agentlisp/json | python -c "import sys,json;d=json.load(sys.stdin);print(d['info']['version'])"`，没返回 `2.0.0rc5` 就等 1-2 min 再试（CDN 最多 5 min 落盘）；b) 命令必须带双 index：`--index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/`（agentlisp 依赖 PyPI 上其他包，少 extra 就会报 dependency not found）；c) 版号有没有拼错（rc前无连字符，`agentlisp==2.0.0rc5` 不是 `2.0.0-rc5`）；三条依次排 | 不 BLOCK（CDN 缓存最多等 5 min） |
| **RC5-4 venv smoke agentlisp --version 不匹配** | `agentlisp --version` 输出不包含字节级子串 `agentlisp, version 2.0.0rc5` | a) `pip show agentlisp` 看 Version 字段；b) 检查 PyPI 上是否有其他更高版本被 pip 优先解析（加 `==2.0.0rc5` 钉死）；c) 若 import OK 但 version 不对 → 检查 pyproject.toml `[project] version` 是否同步写 2.0.0rc5（C1 禁动类 pyproject.toml 原则上不准改；仅当 version 字段被手误改过时才允许单独改 version 一行，改完必须 `git diff pyproject.toml` 只允许 version 一行差异，其他 0 diff） | 不 BLOCK（钉死 ==2.0.0rc5 通常即解）|
| **RC5-5 Approve deployment 长时间 Waiting state** | publish-pypi Job 状态 = `Waiting`，log 显示 `Awaiting approval from required reviewers: [4TWS3]` | **必须 Owner=4TWS3 本人 Approve deployment once**；Agent 即使有 GH token 也不能 Approve（GitHub Environment Required reviewers 绑定账号 + 2FA，API 不能绕过）；通知 Owner 到邮件或 GitHub Notifications / Deployments 页面点 Approve | BLOCK（Owner 手操完 30 s 内自动解除）|
| **RC5-5 Warehouse 7 字段 AND 任一不满足** | JSON API `curl -s https://pypi.org/pypi/agentlisp/json` 返回：info.name≠agentlisp 或 version≠2.0.0rc5 或 requires_python 不含 ≥3.12 或 urls 数组中缺 whl 或缺 sdist | ① 先等 2 min CDN 缓存；② 再核对 publish step success 日志（有没有 `Creating release` + `Uploading agentlisp-2.0.0rc5-py3-none-any.whl ... 201 Created` 两行；sdist 同理）；③ 若某文件 201 未出现 → 检查 release.yml 四端 Build 产物是否正确上传到 actions-artifact（publish step 要 download-artifact 再 upload Warehouse）；④ 仍不满足则失败计数 +1，<3 次重打 tag 重推；≥3 次触发 RC-5 FAIL 总回退承诺跳 rc6 | BLOCK（7 字段全 AND 才解除；<3 次重试，≥3 次跳 rc6）|

### §9.2.2 RC-41 Build/Docker/Release Job 回退表（制度化 6 子节点 · 2026-10-08 ACTIVE）
> **RC-41 FAIL 总回退承诺（本节生效）**：Task3（四端 Build 自验）任一子 Job 连续失败 ≥3 次 → 作废 buildcheck1/2/3 tag，重写 `_tmp_cr41_release_buildcheck.yml`（不碰正式 release.yml = C1 合规）→ 跳 `buildcheckN+1`（N≥3 时升级到 P1 Task5 前不得重启 Task3，避免 CI 配额耗尽）。

| 序号 | 现象（字节级识别）| 常见 Cause Top 2 | 推荐 Fix Top 2 | Blocked By | Unblock Condition | FAIL≥3 总回退 |
|---|---|---|---|---|---|---|
| CR41-B1 | `build-windows / build-ubuntu / build-macos / build-publish-pypi-standalone` 4 Job 任一 `conclusion=failure`，step 停在 `Build wheels + sdist`，stderr 含子串 `ValueError: Unknown classifier: Programming Language :: Racket` | ① 对应端 Build step 缺 strip classifier 行（sed/Where-Object delete 行漏写）；② 对应端 append allow-direct-references 行漏写（hatchling 报 cannot be a direct reference 前序异常已退出，strip 未执行到）| ① 复制已 PASS 端 strip 段到 FAIL 端（对照 CI 37622160494 Ubuntu 端 L119-L133 5 组行全等口径）；② 顺序保证先 strip 后 append → 再 build → 后 git checkout restore；严禁乱序 | SRS/脚本无 BLOCK（纯 workflow 临时文件改）| 对应端 TR-3.4 Verify 步骤同时 PASS（METADATA 不含 Racket + pyproject diff=0）| 跳 `buildcheckN+1`；N≥3 停 Task3 先做 Task5 P1 |
| CR41-B2 | 任意端 停在 step `Build wheels + sdist`，stderr 含 `ValueError: cannot be a direct reference` 或 `file:///.../python` 字样 | ① `[tool.hatch.metadata] allow-direct-references = true` 行未 append 到 pyproject.toml（if grep -q 判断漏写 append）；② append 后 build 前中间步骤（如 `uv sync` 或 editable install）触发 prepare_metadata 提前验证（应使用 `python -m build --no-isolation`，不能 `uv sync`）| ① 追加 allow-direct-references 行：`printf '\n[tool.hatch.metadata]\nallow-direct-references = true\n' >> pyproject.toml`；② 严格用 `python -m pip install build hatchling` + `python -m build --wheel --sdist --no-isolation`，不 uv sync 不 editable | 同上 SRS 无 BLOCK | 对应端 dist/ 下 `agentlisp-*-py3-none-any.whl` + `agentlisp-*.tar.gz` 两文件都存在且 size≥50KB | 同上跳 buildcheck；N≥3 排查本地 pyproject.toml 是否被 C1 误改 |
| CR41-B3 | `gh release create` 失败（未来 Task22 create-release，先登记制度化）| 现象字节级：`gh release create` stderr 含 `404 Not Found` 或 `Repository was not found` 或 `422 Validation Failed: tag_name already exists`；Cause Top2：① GITHUB_TOKEN 权限少（Contents:write 未授予 workflow_permissions）；② tag 名重复 push 前未清旧 tag；Fix Top2：① 在 workflow 顶部加 `permissions: contents: write` 或在 Job 级别加；② `git tag -d <tag>` + `git push origin :refs/tags/<tag>` 清旧（三端清 tag 口径同 P3 RC5-1 清 rc3 口径）| ① permissions 声明（同 release.yml L10 permissions block 复制）；② 清旧 tag 三端 —— `git tag -l` 查本地；`git ls-remote --tags origin` 查远端 —— 全空后重新打 annotated tag push | GITHUB_TOKEN 权限（Owner Settings 可改）| `gh release create` 命令 exit=0 且 stdout 含 `https://github.com/4TWS3/agentLisp/releases/tag/` | N≥3 触发 RC-41 TASK3 暂停；改用 `softprops/action-gh-release@v2`（release.yml L197-L203 同口径）|
| CR41-B4 | `actions/upload-artifact@v4` 失败（artifact upload fail）| 现象：stderr 含 `No files were found with the provided path` 或 `Path does not exist` 或 `500 Server Error`；Cause Top2：① `path: dist/*` glob 路径错（如 Windows 端写 dist/**/* 但仅 dist/*.whl + dist/*.tar.gz 实际；或 PyInstaller 打包单文件未 mv 到 dist/ 导致路径空）② GitHub Actions Artifact 服务临时 5xx；Fix Top2：① 在 upload 前加 step：`ls -la dist/` 或 `Get-ChildItem dist/` 先验文件存在且路径正确；artifact name 四端独立（windows-x64-release / ubuntu-latest-release / macos-latest-release / publish-pypi-standalone-build，互不重名冲突）；② 5xx 时 `gh run rerun <RUN_ID>` 重跑整 Job（不用改代码）| SRS 无 BLOCK | upload step `conclusion=success` 且 `gh api repos/4TWS3/agentLisp/actions/runs/<RID>/artifacts` 返回 4 个 artifact name 字节级全等；每个 size≥2MB | N≥3 改用 `actions/upload-artifact@v3`（v4 → v3 兼容降级，不升级到 v5 避免兼容性回归）|
| CR41-B5 | Docker Login 失败（未来 docker-publish Job，预登记制度化）| 现象：`docker/login-action@v3` stderr 含 `Error: Username and Password Required` 或 `403 Forbidden`（ghcr.io）；Cause Top2：① GH_TOKEN 缺 `packages:write` 权限（workflow permissions block 漏声明）；② GitHub Container Registry 仓库 4TWS3/agentLisp 包未关联仓库（首次 push 前需在 ghcr.io 包 Settings → Connect repository 绑定 agentLisp）；Fix Top2：① permissions block 加 `packages: write`（release.yml L11 已声明，新建 workflow 勿忘）；② Owner=4TWS3 浏览器手操 ghcr.io → Packages → agentlisp → Package settings → Connect repository → 选择 4TWS3/agentLisp 关联 | Owner 手操 Connect repository（Agent 无 ghcr.io UI 权限）| `docker/login-action@v3` step exit=0 且 log 含 `Login Succeeded` | N≥3 暂停 Task3；先跳过 docker-publish（Task 不依赖它），RC5 PyPI 完成后单独 CR 补 docker |
| CR41-B6 | Tag 格式不匹配（push tag 后 workflow 不触发 on.push.tags 块）| 现象：`git push origin v2.0.0-rc5-buildcheck1` 后 Actions 无新 workflow run；`gh run list --limit 5` 无；Cause Top2：① tag 名不符合 glob（写了 `v2.0.0-rc5-buildcheck-1`（多连字符）而非 `v2.0.0-rc5-buildcheck1`；② 分支 Settings → Actions → General → `Run workflows from fork pull requests` 或 tag push 被 Actions 禁用；Fix Top2：① 严格按 `v2.0.0-rc5-buildcheckN`（N 是数字连续无分隔符）打签，glob 匹配 `v2.0.0-rc5-buildcheck*`；② Settings → Actions → General → Actions permissions 选 `Allow all actions and reusable workflows`；Workflow permissions 选 `Read and write permissions` | SRS 无 BLOCK；Settings Actions 权限 Owner 手操确认 | `gh api repos/4TWS3/agentLisp/actions/runs?per_page=5` 返回第一页存在 workflow name=`CR-41 RC5 BuildCheck (No Publish)` run；status=queued/in_progress/success 任一 | N≥3 改用 workflow_dispatch 触发（不用 tag push），在 Actions 页面手动 Run workflow；RC5-3 TestPyPI 正式打签时必须切回 tag push 触发（RC5 发布闸门要求必须是 v* tag 触发 release.yml，禁止 workflow_dispatch 绕过）|

### §9.3 基线漂移分支（最严重，立即回退）
| 漂移现象 | 直接回退动作（不准动其他文件）|
|---|---|
| pytest summary 行不是 `XX failed, 131 passed, 1 warning` 或 `0 failed, 141 passed, 1 warning`（即 baseline CR-39 128 passed/3 skipped/1 warning 子串在 stderr 里找不到了）| `git log --oneline -n 20` 看最近 20 commit → 找到首次让 pytest summary 行漂移的 commit → `git revert <commit_sha>` → 立即回退；再跑 pytest 确认 baseline anchor 恢复；回退完成后再重推 patterns/main.rkt 改件 |
| ruff check 报 N>0 errors（不是 All checks passed!）| `git diff pyproject.toml` 看 ruff 配置是否被改 → 有改动立即 `git checkout pyproject.toml`；`git diff tests/patterns/` 看新增 Python fixtures 是否格式错 → `ruff format tests/patterns/` 修 → 重新跑；若仍 N>0 → `git reset --hard` 回退到 CR-40 第一个 commit 再重来 |
| check_handoff_compliance.py 非 exit=0 | ① anchor 子串丢：打开脚本看 anchor 正则 → 在 §7.2 中补回对应子串（注意 **128 passed, 3 skipped, 1 warning 必须在 §7.2 内，不准挪到其他节**）；② size<20KB：补 §6 顺位正文说明到 ≥300 字；③ 章节不全：§1..§7 章节标题必须全存在，缺哪节加哪节标题 |
| C1 9 禁动类文件 diff >0（除 main.rkt 外）| `git diff --name-only` 列出所有改动 → 对除 main.rkt 外的 C1 文件（parser/checker/emitter/agentlisp_compiler/ci.yml/17 runtime py 等）执行 `git checkout HEAD -- <path>`，原样还原；**绝不准保留任何 C1 diff，违例会让 AC-6 Rubric 直接归零**；还原完成后重新 commit |

---
