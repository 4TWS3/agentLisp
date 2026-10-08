# CR-41 独立 Agent Review Report（只读审计，不可改代码）

## 元信息

| 项 | 值 |
|---|---|
| 审计人 | 独立 Fresh Agent（全新会话，未参与 CR-41 实现；DSH_SESSION_ID = `01b325d9-85dd-4346-b038-b4c33fc7b0a0`，parent session-0ea5a01d-4fb4-49bf-857c-7a4fe7123aa0） |
| 审计时间 | 2026-10-09 00:20–00:45（+0800） |
| 被审 HEAD | `dd3cecc53caa1b29928b2fb05fca609bd770da5f`（2026-10-09 00:20:14 +0800 · "CR-41 V2 pattern layer REBUILD -- Core-AST-legal templates + real verification gates (GREEN)"） |
| 审计模式 | 只读：除本文件外未修改任何仓库文件、未 git commit、未打 tag |
| 本机环境 | macOS · Racket 8.12（`.racket/bin`）· Python 3.12.7 · pytest 9.0.3 |

### ⚠️ 审计时的仓库状态（必须先声明，否则所有"字节级证据"都会被误读）

`git status --short` **不是干净的 HEAD 检出**：

```
 D docs/agentlisp-pattern-macros-tech-spec.md
 M docs/spec/agentlisp_srs.md
 M tests/test_check_roadmap_traceability.py
?? .trae/
?? docs/handoff/20261008_cr41_patterns_v2_stage0_to_stage1_handoff.md
?? docs/spec/agentlisp-pattern-macros-tech-spec.md
?? docs/spec/agentlisp-rsi-evolution-tech-spec.md
```

即：**SRS 升级、CR-41 handoff、spec.md/tasks.md 全部未提交**（`.trae/` 与 CR-41 handoff 均为 untracked；SRS 的 5 处升级是工作区未提交改动）。本报告对"HEAD dd3cecc"与"工作区"分别取证，凡涉及 SRS/handoff 的行号均以审计时工作区快照为准：

- CR-41 handoff sha256 = `3373a1bd499eff9abcf5d8c6b3284a55927ed9b5fdcef343fb04e7177058a214`（57940 B，mtime 2026-10-09 00:28:28）——**该文件在本次审计进行中被外部改动过**（00:25 时 57334 B → 00:28 时 57940 B），故其行号证据可能随写手继续变动。
- SRS sha256 = `f43a29489a448074941557b2b2bc7b32869c8da57391f5bab922092f0733b6ab`
- tasks.md sha256 = `100fe1e1fbfeb492b08a86afa8ac0578d94f451b89b50bbc702491d8060fb902`

### CI 三绿证据（审计人实跑，原文粘贴）

1. **CI Run 37807999282 = success**（`gh run view 37807999282`；workflow = *O13 Patterns MVP Standalone Verify (temp CR-40b)*；event=push；headSha=`dd3cecc`）。**注意：dd3cecc 上只有这一个 temp workflow 的 run，没有 ci.yml run**（`gh run list` 该 SHA 仅返回 37807999282 / 37807997994，均为同一 temp workflow）。
   - `verify-patterns-mvp Run pytest patterns cases` → `PATTERNS V2 AST OK (30/30 legal Core AST)` + `70 passed, 1 warning in 36.82s`
   - `Run RackUnit patterns MVP` → `5 success(es) 0 failure(s) 0 error(s) 5 test(s) run`（V1）+ `10 success(es) 0 failure(s) 0 error(s) 10 test(s) run`（V2）
   - `Verify 5 macros standalone expand against fixtures` → `SUMMARY failures=0/5` **（只有 V1 5 宏，见 AC-1）**
   - `V2 end-to-end compile probe (报告型：C1-blocked，非阻塞)` → `V2-COMPILE ok=0 fail=30`、`probe compiler/agentlisp_compiler.rkt: BROKEN`、`probe compiler/checker.rkt: BROKEN`
2. **审计人本机复跑（逐条原文）**：
   - `python3 scripts/check_patterns_v2_ast.py` → `checked 30 fixtures` / `PATTERNS V2 AST OK (30/30 legal Core AST)` / exit=0
   - `python3 -m pytest tests/patterns/ -q --no-cov` → `70 passed in 29.40s` / exit=0（V1 10 + V2 30 + NFR01 15 + NFR02 15）
   - `racket compiler/tools/check_v2_compile.rkt` → `probe compiler/patterns_v2.rkt: OK` + C1-BLOCKED 三缺陷原文（见争议点 4）
   - RackUnit：CI 原文 V1 `5 success(es)`、V2 `10 success(es)`（本机未另跑 raco test；以 CI 原文为凭）
   - `python3 scripts/check_handoff_compliance.py --handoff <CR-40> --handoff <CR-41>` → `HANDOFF OK [2026-10-09] ... (size=56.0 KB · 7 章全 · 四硬锚 6/6 · §6 顺位充足)` exit=0
   - `git diff HEAD <C1 6 件> | wc -c` → `0`；`git diff 03bb804 <C1 6 件> | wc -c` → `0`
   - `grep -n CR41_BASELINE_PASSED_COUNT docs/spec/agentlisp_srs.md` → L289 `CR41_BASELINE_PASSED_COUNT: 158`
   - ⚠️ `python3 scripts/check_roadmap_traceability.py`：**带 Racket PATH 时 exit=0（warn rows=47）；不带 Racket PATH 时 exit=1**（`ROADMAP-BASELINE-MISMATCH: L274=158 actual=125`）——详见 AC-7。

---

## 一、11 条验收标准逐条评分（spec.md §Acceptance Criteria，0–5）

| 编号 | 标题（spec.md AC） | 评分 | 打分依据（审计人实跑的文件/行号/命令输出） |
|---|---|---:|---|
| AC-1 | Pattern V2.1 10 宏三绿闭环（rule） | **3 / 5** | ②③④ 达标：run 37807999282 conclusion=success；`70 passed`（含 V2 30）；RackUnit V1 5/5 + V2 10/10。**① Standalone `failures=0/20` 不达标**：`.github/workflows/_tmp_o13_patterns_mvp_verify.yml` L42-139 的 standalone 步骤只 require `compiler/patterns.rkt`（L51），只列 5 个 V1 宏（L87-122），L132 打印 `printf "SUMMARY failures=~a/5"`，CI 日志原文 `SUMMARY failures=0/5`；**全 workflow 无任何 V2 standalone 步骤**，V2 的 10 个 HC 只被 RackUnit（`compiler/tests/test_patterns_v2_mvp.rkt` L64-74，10 case）覆盖，GENERIC 分支无独立 standalone 证据。4 条 AND 条件缺 1 条核心闸门 |
| AC-2 | C1 禁动类 6 core diff=0（零容忍） | **5 / 5** | `git diff HEAD compiler/checker.rkt compiler/parser.rkt compiler/emitter.rkt compiler/agentlisp_compiler.rkt .github/workflows/ci.yml pyproject.toml \| wc -c` → **0**；AC-2 指定锚 `git diff 03bb804 --stat -- <同 6 件> \| wc -c` → **0**。字节级空输出，exit=0。C1 红线真实守住 |
| AC-3 | GAP-1 落地 NFR-PATTERN-01/02 Scn=Pas 0→15（rule） | **3 / 5** | 字面条件达标：附录 B `| **NFR-PATTERN-01** | 15 | 15 |`、`| **NFR-PATTERN-02** | 15 | 15 |`（SRS 附录 B 第 44/45 行）；`check_roadmap_traceability.py` 三集合 48-ID 全等（无 ROADMAP-ID-MISMATCH）、ScnSum=PasSum=168。**但"落地"是名义的**：`compiler/patterns_checker_v2.rkt` L211-227 的入口 `run-patterns-checker-v2` **在整个仓库内无任何调用点**——`compiler/main.rkt` L107-110 只是 `(void (eval '(lambda (get-hc-exp get-hc-hw get-gen-exp) (run-patterns-checker-v2 ...)) ns2))`，把过程构造出来即丢弃，从不 apply（实跑 `racket compiler/main.rkt --dump-ast <fixture>` stderr 为空、无任何 checker 输出）。真实断言全部在 Python 侧 `tests/patterns/test_pattern_checker_v2.py`。且 SRS 行内引用的测试 ID 不存在（见 AC-9） |
| AC-4 | HAN-GAP-01 修复 18→16（rule） | **5 / 5** | CR-40 handoff：`远期 16 件` 命中 L195 / L278 / L347 / L384 共 4 次（TR-1.2 ≥3 达标）；AC-4 正则 `远期.*18件\|远期.*18 件\|18件未实现` 在两份 handoff 上 **0 命中**。§8 第 8 号行（L347）、§6.2 顺位 1（L278）、§9.1 GAP 登记（L384）三处口径统一为 16 件 |
| AC-5 | release.yml 四端 Build 自验 4/4（rule） | **4 / 5** | `.github/workflows/_tmp_cr41_release_buildcheck.yml` 存在；`gh run view 37732081123` → conclusion=success，4 个 job 全 success（Build Windows x64 / Ubuntu / macOS / Publish-PyPI Standalone）；日志 `checkout -- pyproject.toml` 命中 **4** 次、`allow-direct-references` 命中 20 次。**扣分**：成功 run 的 headSha = `46cdede`（不是被审 HEAD `dd3cecc`，相隔 2 个 commit），且它由 tag `v2.0.0-rc5-buildcheck2` 触发；AC-5 Given 写的是 `v2.0.0-rc5-buildcheck1`，而 buildcheck1 实际指向 `ccaa2e97`（对应 run 37730931293/37730938172 = failure）。"4 whl+sdist 产出件字节级存在"未在本次时间盒内取 SHA256 |
| AC-6 | handoff §9.2/9.2.1 Docker + Create Release 回退树补齐（rule） | **3 / 5** | **AC 的字面 grep 契约不达标**：`grep -cE "docker login fail\|docker buildx fail\|docker push fail\|gh release create fail\|artifact upload fail\|tag mismatch"` → CR-40 handoff **1**、CR-41 handoff **0**（Pass Condition 要求 =6）。实质内容存在：CR-40 handoff §9.2.2（L421-431）登记 6 行 CR41-B1..B6（Build 四端 / direct reference / gh release create / artifact upload / Docker Login / Tag 格式），每行均含 Cause Top2 + Fix Top2 + Blocked By + Unblock Condition 字段。落差根因是文案用中文"失败"而非 AC 的英文 `fail`。另：AC/FR-CR41-07 说"§9.2.1"，实际新表落在 §9.2.2（§9.2.1 已被 RC-5 PyPI 占用） |
| AC-7 | 三验 exit=0（pytest + roadmap + handoff）（rule） | **2 / 5** | **三项均不可复现声明的字节级基线**：① `python3 scripts/check_roadmap_traceability.py` **不带 Racket PATH 时 exit=1**，stderr 原文 `ROADMAP-BASELINE-MISMATCH: L274=158 actual=125 (actual < 声明值...)`；带 Racket PATH 才 exit=0。② `python3 -m pytest --strict-markers -q`：无 Racket → **`128 passed, 73 skipped, 1 warning`**（≠158/3/1）；有 Racket → **`3 failed, 192 passed, 3 skipped`（exit≠0）**，失败 3 条：`test_cli_if_cli_1_all_flags_and_6_exit_code_encoding` / `test_emit_context_auto_append_maps_to_underscore_key_in_python_source` / `test_nfr_perf_2_compile_wall_clock_lt_200ms`。③ 只有 handoff compliance exit=0。声明值 158 在本机两种模式下都不成立 |
| AC-8 | Pattern V2.1 完整性（rubric ≥4） | **3 / 5** | 30 对 fixture 齐备、pytest 30 case 全绿、200 字节前缀全等；`tests/patterns/test_pattern_checker_v2.py` L107 断言 `nout[:200] == expected_src[:200]`；完整 AST 全等只在 HC 场景（L283-286，10 宏）。**未达 5 分的硬缺口**：(a) `.expected.rkt` 30 份由 `scripts/gen_patterns_v2.py` 与 `patterns_v2.rkt` **同一份 PATTERNS/template_of 源**生成（L283-314 与 L372-389），且 `constants` 与提交文件 100% 一致（审计人内存重算：`emit_racket() == committed` True、stale count 0/30）——它是"同源双实现交叉校验"，不是独立规格快照；(b) 无反例 fixture 验证"宏展开错误时 messages 具体到 srcloc 行号列号"（anchor 5 明确要求），全部 30 case 只断言 rc==0 |
| AC-9 | 可追溯性与三射表质量（rubric ≥4） | **3 / 5** | 达标部分：SRS 孤儿 48-ID 裸逗号登记、`check_roadmap_traceability.py` ID 三集合全等无 MISMATCH、CR-40 §8 含 10 个 CR41-PAT 行。**扣分**：(a) §8 三射表仅 **28 数据行**（`grep -c '^|'` = 30，含表头+分隔），AC-9 anchor 5 要求"总行数 ≥48"；(b) SRS 附录 B 引用的测试 ID **不存在**——`test_nfr_pattern_01_v2_15macros_30cases_ast_byte_equal_via_sexpr_same`、`test_nfr_pattern_02_static_safety_8d_matrix_120checkpoint_all_true` 在仓库中 0 命中，实际为 `test_nfr01_macro_expand_head200_prefix_byte_identical` / `test_nfr02_static_safety_8d_matrix_120checkpoint_all_true`；(c) SRS CR41-PAT01/02 行引用的 fixture 名 `fixtures_v2/cr41_pat01_priority_*` 不存在（实际 `priority01_hc_HC.al` 等） |
| AC-10 | 合规与零回退质量（rubric，**必须=5**） | **4 / 5** | 达标：C1 6 件 diff=0（HEAD 与 03bb804 双锚）；`scripts/_tmp_bracket_diff.py compiler/patterns_v2.rkt` → `sq=0 par=0`，`patterns_checker_v2.rkt` → `sq=0 par=0`；`git ls-remote --tags origin \| grep -c 'v2.0.0-rc5$'` = **0**，本地 tag 亦 0（仅 buildcheck1/buildcheck2）。**扣分点**：anchor 5 要求"skip-existing 制度化在 release.yml **两处**都为 false"，实测 `grep -rn 'skip-existing' .github/workflows/` 全仓库**只有 1 处**（release.yml:350，值确为 false，publish action 也只有 1 个 pypa/gh-action-pypi-publish@release/v1）——"两处"这一判据在当前产物上不可满足/不可核验。零容忍口径下不给满分 |
| AC-11 | 文档零上下文接手质量（rubric，**必须=5**） | **2 / 5** | 达标：§0 30 秒启动入口存在（CR-41 handoff L7-18）；`check_handoff_compliance.py` exit=0。**硬缺口**：(a) 文档 **57940 B = 56.6 KB < NFR-CR41-06 要求的 ≥140KB**（anchor 5 "size≥140KB" 直接不达标）；(b) anchor 5 要求的 §5.2 端点表与 §9.2.1 回退树**不在 CR-41 handoff 中**（CR-41 handoff 章节目录只有 §0–§7，§5.2/§9.2.1 在 CR-40 handoff）；(c) 文档自述 HEAD = `6969c35`（L20），实际 HEAD = `dd3cecc`；(d) 文档引用的最终 CI 是 `37793031537`（L75/L83），审计人实测该 run **conclusion=failure**（headSha 6969c35），而真实成功 run 是 37807999282；(e) 行数陈旧：§3.1 称 patterns_v2.rkt "405 行"实测 221 行、§3.2 称 228 行实测 227 行；(f) NEXT3 自带模板的 AC 编号（AC-5=NFR01、AC-7=NFR02、AC-10=22Task）与 spec.md 的 AC-1..11 编号**不是同一套** |

**分数汇总：AC-1=3, AC-2=5, AC-3=3, AC-4=5, AC-5=4, AC-6=3, AC-7=2, AC-8=3, AC-9=3, AC-10=4, AC-11=2**

---

## 二、5 个争议点逐条判断

### 争议点 1：NFR-PATTERN-02 断言数 150 → 120 是否正当？覆盖是否有替代？

**判断：技术降级正当，但只降了一半（Python 侧降、Racket 侧没降），且"替代覆盖"不能覆盖被删维度原本想表达的模式语义。**

证据：
- 被删的两维确实是非法键。`compiler/agentlisp_compiler.rkt` 的每段 key 白名单是硬编码的 `keyword-kvs`（L146 `:model`、L169 `:context`、L257 `:constrain`、L273 `:verify`、L286 `:correct`），全文 **0 处** `:pattern-kind` / `:pattern-config`（`grep -n 'pattern-kind\|pattern-config' compiler/agentlisp_compiler.rkt compiler/parser.rkt` 空输出）。产物含之即无法通过编译，故此二键不能作为"静态安全"判据——降级理由成立。
- 但同一断言集存在**两个互相矛盾的实现**：Python 侧 `tests/patterns/test_pattern_checker_v2.py` L130 `EIGHT_CELL_KEYS` = 8 维 × 15 宏 = **120**；Racket 侧 `compiler/patterns_checker_v2.rkt` L170-171/L187-188/L196-207 仍是 **10 维（含 `pattern-kind-tag-present?` cp3、`pattern-config-kv-present?` cp4）× 15 = 150**。CR-41 handoff 也仍多处写 150（L150 "NFR01 30 + NFR02 150 = 180"、L170/L176/L249/L272/L415），直到 L506 才出现 120 的修正说明。**三件产物（测试/checker/handoff）口径不一致**。
- 替代覆盖的真实强度：8 个 cell 是 d1-1 5-bucket 升序、d1-2 三必块、d3-1 harness c/v/c、d3-2 无 eval、d4-1 name 是 symbol、d4-2 block 数 ∈[3,5]、d5-1 顶层 define-agent、d5-2 每 block 带 kw tag —— **100% 是语法/结构不变量，没有一个 cell 断言模式语义**。被删维度原本承载的"pattern-kind/pattern-config 即模式身份与配置"的表达能力，在替代方案里**没有等价物**（语义被搬进了 system-prompt 字符串，见争议点 2）。

### 争议点 2：30 份 .expected.rkt 由 gen_patterns_v2.py 生成 —— 快照式自证还是可接受的"规格→fixture 单一事实源"？

**判断：介于两者之间，偏"可接受但不充分"。它比纯自证强（存在真实 Racket 展开路径 + 独立 Python 复算），但绝不能被当作 SRS 语义符合性证据——因为没有任何测试断言 SRS L104-113 的语义标记。**

证据：
- 不是纯自证的部分：30 条 pytest 真的调用 Racket——`test_pattern_checker_v2.py` L56-67 `_racket_macroexpand_v2` 起 `racket compiler/main.rkt --dump-ast <al>`，再与 .expected.rkt 比 200 字节前缀（L107）；HC 场景在 L283-286 做完整 AST 全等。Racket 侧替换函数（`patterns_v2.rkt` 的 `v2-instantiate`）与 Python 侧 `instantiate` 是两套独立实现，故能抓替换机制 bug。
- 是自证的部分：两条通路的**模板数据同源**——`scripts/gen_patterns_v2.py` L156-191 `template_of()` 既喂给 `emit_racket()`（L283-314）生成宏，又喂给 `emit_fixture()`（L372-376）生成 30 份 expected。审计人内存重算确认提交文件与生成器 100% 一致（`emit_racket()==committed` True、30/30 无 stale）。因此**模板本身写错/漏写语义时，两边会一起错、测试必然全绿**。
- 关于"模板是否落实 SRS L104-113 每条语义标记"：审计人逐条核对 SRS L104-113 与生成器 `PATTERNS`（L50-124），**10 个模式各 3 条 markers 全部存在**，且结构性要求也落地：PAT02 注入 `decomp-level-1/-2` 两个 scoped-worker ✓、PAT04 `:verify :reviewer-agent` ✓、PAT05 `topic-processor` ✓、PAT08 `(:constrain :require-human-approval (all))` ✓、PAT09 `:max-retries 3` ✓、PAT10 `:on-failure ask-human` ✓。**但**：PAT03 `状态可达性 ≥2 静态断言`、PAT06 `2 条 decomposer-schema-field-type-check 注入 Constrain 段`、PAT07 `on-violation Verify→Correct 回路`、PAT09 `3 层 retry + backoff=1.5x` 这些语义**只以字符串形式存在于 :system-prompt**，Core AST 里没有任何可执行结构承载（marker 文案自称"Constrain 段注入"，实际 Constrain 段只有 `:require-human-approval` / `:forbidden-commands`），SRS 原文的"声明/注入/断言"落在产物上被弱化为提示词文本。
- **tests 对这些标记做断言了吗？答案：Racket/pytest 层没有；只有 Python 闸门脚本有，且 oracle 是生成器自己。** NFR02 的 8 个 cell（上述）**零标记断言**；NFR01 的 V2 分支靠"与同源 expected 全等"，同样不可能发现标记缺失。唯一检查标记的地方是 `scripts/check_patterns_v2_ast.py` L281-283 `for mk in markers: if mk not in prompt`，而 `markers` 与 `prompt` 都由 `gen_patterns_v2.PATTERNS` 产生——**自己验自己**，SRS 文本与 markers 之间没有任何机器校验。

### 争议点 3：AC-1① 要求 Standalone failures=0/20 —— CI 是否真覆盖 V2 的 20 分支？

**判断：未覆盖。CI 只覆盖 V1 5 宏（`SUMMARY failures=0/5`），V2 的 20 个 HC/GENERIC 分支没有任何 standalone 证据。AC-1 不达标，必须如实扣分。**

证据（`.github/workflows/_tmp_o13_patterns_mvp_verify.yml`）：
- 步骤名就是 `Verify 5 macros standalone expand against fixtures (NO main.rkt wiring)`（L42）；heredoc 里只 `(require "compiler/patterns.rkt")`（L51），5 次 `check-macro` 全是 V1（L87-122）；结果行 `printf "SUMMARY failures=~a/5\n"`（L132）。
- CI 日志原文（run 37807999282）：`SUMMARY failures=0/5`（出现 2 次，L369/L380 of /tmp/ci.log）。
- 全 workflow 检索无 V2 standalone 步骤；V2 的独立展开只在 RackUnit `compiler/tests/test_patterns_v2_mvp.rkt`（require "../patterns_v2.rkt"，L10；10 个 HC case，L64-74）——HC-only 10 条，且属于 AC-1③ 的计分口径，不能重复计入 ①。
- spec.md L73 把 ① 写成 `failures=0/20（10 宏×HC/GENERIC 双分支）`，AC-1 的 Then 还强调"3 条 VERBATIM 字节级条件（AND 关系）"。当前交付缺 1 条，且缺口正好是"冻结前唯一能证明 V2 宏可独立展开（不依赖 main.rkt 接线）"的那条。

### 争议点 4：C1 三既存缺陷导致 CLI 编译路径全死 —— 验收边界是否被诚实标注？

**判断：三缺陷全部独立复现，且"报告型闸门"的标注方式基本诚实（步骤名/注释/工具输出三处都写明 C1-blocked、continue-on-error）；但归因不完整——存在一个不属于 C1 禁动类的 main.rkt 级阻断，且"V1 0/5"实为 0/10，边界描述有偏差。**

审计人独立复现（Racket 8.12，本机）：
- **缺陷①** `python3 scripts/_tmp_bracket_diff.py compiler/agentlisp_compiler.rkt` → `final bracket balance sq=0 par=-2`，`FIRST NEGATIVE par depth=-1 at L120`。
- **缺陷②** `racket -e '(require (file "compiler/checker.rkt"))'` → `compiler/checker.rkt:102:65: struct: multiple #:inspector, #:transparent, or #:prefab specifications / at: #:prefab / in: (struct srcloc* (source line column position span) #:transparent #:prefab)`。
- **缺陷③** `compiler/parser.rkt` L13 `(struct al-agent (name purpose tools harnesses workflows hooks) #:transparent)` = 6 字段，L54 `(al-agent (ensure-string/sym name) purpose tools workflows hooks)` = 5 参 → `racket compiler/main.rkt -i <任何 .al> --check-only` 报 `al-agent: arity mismatch; expected: 6; given: 5 ... parser.rkt:22:0: parse-s-exp`。
- **全量矩阵（审计人实跑）**：`tests/patterns/fixtures_v2/*.al` → **ok=0 fail=30**（30/30 同一签名 al-agent arity）；`tests/patterns/fixtures/*.al` → **ok=0 fail=10**（注意：不是 0/5，V1 fixtures 目录有 10 个 .al）；`examples/production-repair-agent.al --check-only` → rc=1。
- **标注诚实性（正面证据）**：workflow L181-185 有 6 行注释逐条列 ①②③；步骤名 `V2 end-to-end compile probe (报告型：C1-blocked，非阻塞)` + `continue-on-error: true`；日志打印 `V2-COMPILE ok=0 fail=30 (C1-blocked，非阻塞)` 与 `C1-BLOCKED: agentlisp_compiler par=-2 / checker.rkt srcloc* / parser.rkt al-agent arity 5v6`；`compiler/tools/check_v2_compile.rkt` L1-12 与运行输出同样自述 C1-BLOCKED 且恒 exit 0。**没有把死掉的编译通路伪装成绿**。
- **归因不完整的证据（新发现，非 C1）**：审计人对 `/tmp/empty.al`（**空文件，零 agent form**）跑 `racket compiler/main.rkt -i /tmp/empty.al --check-only` → rc=1，stderr `application: not a procedure; expected a procedure that can be applied to arguments / given: (al-ast '() '() '()') / context...: body of "compiler/main.rkt"`。空输入根本不会触发 parser.rkt 的 al-agent 构造，故此错误**独立于 C1 三缺陷，位于 `compiler/main.rkt`（不在 C1 6 禁动清单内，且 CR-41 已改过该文件 22 行）**。`examples/production-repair-agent.al`（顶层用 `defagent`）也复现同一签名。这意味着"修好 C1 三项即可启用端到端闸门"的承诺**尚未被证实**，handoff 与 workflow 注释的因果关系链缺一环。

### 争议点 5：SRS 附录 B 的 AC-2 矩阵行 128 → 158 —— 正当基线演进还是锚点漂移？

**判断：性质上是"正当的基线演进"，但执行方式造成了两个副作用——永久锚 128 退化为不可机器校验的 prose，且新基线 158 在审计机上无法复现；脚本的 mismatch 语义又只查"actual < declared"，使下调声明天然免检。**

证据：
- 机器校验三向（脚本 `check_roadmap_traceability.py` L183-235）读取的是：`CR41_BASELINE_PASSED_COUNT`（优先于 `CR39_BASELINE_PASSED_COUNT`）→ 附录 B `| **AC-2** |` 行的 Scn/Pas 两列 → 运行时 actual。当前三者 = 158/158/158（SRS L289 键值行 + 附录 B 行），内部自洽 → 无 `ROADMAP-BASELINE-MISMATCH`（带 Racket 时）。
- L288 prose 确实**完整保留**了 CR-39 GA `CR39_BASELINE_PASSED_COUNT: 128` 与"128 永远不变"的表述。但脚本的 `v1` 取值一旦命中 `CR41_BASELINE_PASSED_COUNT` 就**再也不会读 CR39 值**（L185 的 `or` 短路），即 128 从此不在任何断言里，仅靠人读 prose 维持。这就是"锚点从机器契约降级为文档承诺"。
- 更实际的问题是声明值本身：审计机（无 Racket PATH）`pytest --strict-markers` = `128 passed, 73 skipped`，roadmap fallback（deselect 该测试文件 3 条）= 125 → `actual < declared` → **exit=1**；带 Racket = 192 passed + 3 failed。**158/3/1 与 188/3/1 两个声明基线在本机均不可复现**。
- 叠加脚本自身的不对称：L232 只判 `val < declared`（注释明说"≥ 声明值的正向 E2E Bonus 不计 mismatch"），而工作区里 `tests/test_check_roadmap_traceability.py` 的改动也承认"脚本只判 actual < declared，因此「下调声明值」天然安全、抓不出来"。即基线演进方向上，闸门只防丢测试、不防虚报。

---

## 三、Actionable Findings（PASS 必须精确 0 条；当前 **11 条** → FAIL）

1. **`.github/workflows/_tmp_o13_patterns_mvp_verify.yml:42-139`** — standalone 闸门只覆盖 V1 5 宏（`SUMMARY failures=0/5`），spec AC-1① 要求的 V2 20 分支（10 宏 × HC/GENERIC）无证据。建议：新增 V2 standalone 步骤（require `compiler/patterns_v2.rkt`，遍历 `fixtures_v2/*_hc_HC.al` 与 `*_generic_GENERIC.al`），打印 `SUMMARY failures=0/20`。
2. **`compiler/main.rkt:107-110`** — `(void (eval '(lambda (get-hc-exp get-hc-hw get-gen-exp) (run-patterns-checker-v2 ...)) ns2))` 只构造过程不调用，`patterns_checker_v2.rkt` 全部 227 行是死代码（全仓库无第二调用点）。建议：真正 apply 该过程并断言 pass/fail，或在测试里直接 require 并调用。
3. **`compiler/patterns_checker_v2.rkt:170-171,187-188` vs `tests/patterns/test_pattern_checker_v2.py:130`** — NFR02 维度数自相矛盾（Racket 10 维/150 cell 含非法键判据，Python 8 维/120）；`docs/handoff/20261008_cr41_...md:150,170,249,272,415` 仍写 150。建议：三处统一为 8 维/120 并同步 SRS 附录 B 注释列。
4. **无任何 AST/RackUnit 层断言 SRS L104-113 的模式语义标记**（`test_pattern_checker_v2.py:130` 的 8 个 cell 全为结构不变量）；唯一标记检查 `scripts/check_patterns_v2_ast.py:281-283` 的 oracle 是生成器自身的 `PATTERNS[*]['markers']`。建议：新增"SRS 行号 ↔ marker 文本"独立映射校验，或在 RackUnit 层断言 10 宏各 3 条标记。
5. **`docs/spec/agentlisp_srs.md` L289 + `scripts/check_roadmap_traceability.py`** — 声明基线 158 在无 Racket 环境下不可复现（实测 128 passed/73 skipped；roadmap fallback 125）→ 门禁 exit=1；带 Racket 全量 pytest exit≠0。建议：在固定环境重钉基线，并把 roadmap 门禁改成对"缺失测试集合"而非绝对数敏感。
6. **`runtime/tests/test_cli_if_cli_1_exit_encoding.py:86` / `runtime/tests/test_harness_v2.py:1832,~1892` / `runtime/tests/test_v2_smoke.py`** — 有 Racket 时 3 条 hard-assert 失败；ci.yml 的 python-tests 矩阵不装 Racket，故 CI 永久看不到。建议：修 CLI 通路或在 CI 显式安装 Racket 并纳入门禁（否则"三绿"只是摘樱桃口径）。
7. **`compiler/main.rkt`（非 C1 文件）** — 空 .al 输入即 rc=1：`application: not a procedure; given: (al-ast '() '() '()')`。workflow L181-185 与 `compiler/tools/check_v2_compile.rkt:4-12` 把 CLI 全死归因于 C1 三缺陷，但此签名独立于 C1。建议：修正归因文字，并修复/park main.rkt 的该缺陷后再承诺"修 C1 即通"。
8. **`docs/spec/agentlisp_srs.md` 附录 B** — 引用了不存在的测试 ID（`test_nfr_pattern_01_v2_15macros_30cases_ast_byte_equal_via_sexpr_same`、`test_nfr_pattern_02_static_safety_8d_matrix_120checkpoint_all_true`）与不存在的 fixture 名（`fixtures_v2/cr41_pat01_priority_*`）。建议：改为真实 ID（`test_nfr01_macro_expand_head200_prefix_byte_identical`、`test_nfr02_static_safety_8d_matrix_120checkpoint_all_true`）与真实文件名（`priority01_hc_HC.al`）。
9. **`docs/handoff/20261006_cr40_...md:426-431`** — AC-6 的 VERBATIM grep 契约不达标（`fail` 系关键词 count=1，要求 6），因文案用"失败/格式不匹配"中文。建议：在 6 行现象列补英文 token（如 `docker login fail`）或按实际文案修订 AC-6 的正则。
10. **`.trae/specs/no_pypi_cr41_patterns_v2_1/tasks.md`** — 22 个 Task 仅 2 个 `completed`（T1/T2），其余 20 个（含 T8-T17 十个宏、T18 checker、T19 基线、T20 三射表、T21 review、T22 收尾）仍为 `pending`，与 handoff/commit message 宣称的 "22/22 Tasks 全闭环" 矛盾。建议：逐条回填 Status + Completion Evidence，或把宣称降级为"代码已落地、任务台账未更新"。
11. **`docs/handoff/20261008_cr41_...md`** — ① 体积 57940 B < NFR-CR41-06 的 ≥140KB；② 缺 AC-11 anchor 5 要求的 §5.2 端点表与 §9.2.1 回退树（在 CR-40 handoff，需在 CR-41 handoff 内引用/内联）；③ 自述 HEAD `6969c35` 与实际 HEAD `dd3cecc` 不符；④ 引用的最终 CI `37793031537` 实测 conclusion=**failure**（应由 37807999282 取代）；⑤ §3.1 "405 行" / §3.2 "228 行" 与实测 221 行 / 227 行不符。建议：全面回填并对 CI run ID 做一次 grep 自检。

（非 finding 的补充说明：AC-5 的成功 buildcheck run 37732081123 位于 `46cdede`，由 `v2.0.0-rc5-buildcheck2` 触发；`v2.0.0-rc5-buildcheck1` 指向失败的 `ccaa2e97`。release.yml 的 `skip-existing: false` 全仓库仅 1 处而非 AC-10 所称"两处"。）

---

## 四、最终判定

**FAIL**

判定依据（严格按 spec.md AC 与 handoff NEXT3 的 PASS 条件）：**所有 AC≥3 不满足**（AC-7=2、AC-11=2 低于阈值），**AC-10=4 ≠ 5**（零容忍项未满分），**Actionable Findings = 11 ≠ 0**。三条独立否决理由同时成立。

诚实性说明：本次审计确认了 CR-41 的三项真实成果——C1 六件 diff 严格为 0（AC-2=5）、V1/V2 宏的 pytest 70/70 + RackUnit 5/5 + 10/10 + AST 30/30 全部实跑可复现、编译通路的死亡被 workflow/工具以 continue-on-error + 显式 C1-BLOCKED 文案如实公示而非粉饰。**但**"三绿闭环"缺了自定的 Standalone V2 20 分支、"GAP-1 落地"的核心模块从未被执行、"22/22 任务闭环"台账只有 2/22、声明基线 158 在本机不可复现、端到端闸门死因被不完全归因于 C1。这些是必须返修的实质缺口，不是文档瑕疵。

返修优先级建议：F1（V2 standalone 20 分支）→ F2（checker 真正接线，否则 GAP-1 名存实亡）→ F3/F4（120 vs 150 口径统一 + 语义标记独立断言）→ F5/F6/F7（基线复现性与 CLI 阻断归因）→ F8-F11（台账/文档回填）。
