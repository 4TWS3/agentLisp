# AgentLisp 踩坑台账（CR-42 起）

> 规则：每个坑必须写清「现象 / 根因 / 现在靠什么守」。
> 「守」一栏必须是可执行的判据。没有判据的坑标「仅纪律」，并登记原因。

## 一、有判据守护的坑

| # | 现象 | 根因 | 现在靠什么守 |
|---|---|---|---|
| 1 | 产物工具字段恒为空 | `parse-tools` 把结果 hash 写在 `if` 之后，递归返回值被丢弃，用初始空累加器构造结果 | `tests/test_compiler_end_to_end.py` 断言产物含源里的工具名与 prompt 原文 |
| 2 | 加 `:pattern` 后 checker 25 格失败 | `check-prefix-sorted-5-bucket` 要求每块 `bucket->idx < 5`，正交块 idx=999 | `test_pattern_checker_v2.py` NFR 矩阵 + `check_patterns_v2_ast.py` |
| 3 | Python 侧判据与 Racket 侧漂移 | 两侧各写一份 cell 逻辑（d4-2 块数） | NFR 测试逐格比对两侧结果 |
| 4 | 夹具展开了但没进产物 | `main.rkt` 的 `pattern-macro-names` 白名单没登记新宏 | `tests/test_cr42_pitfall_guards.py::test_all_v2_macros_are_whitelisted` |
| 5 | 8 维矩阵 d1-2 判假，展开命中失败 | 夹具里的 agent 名写成文件名（`x_hc_HC`），HC 分支按 `x_hc` 匹配 | `...::test_fixture_agent_name_matches_key_scene` |
| 6 | 语义又回到提示词里 | `prompt_of` 把 markers 拼进 system-prompt | `...::test_no_prompt_only_semantics_in_fixtures` |
| 7 | 模式覆盖静默退化 | 新增/改动 kind 后没有产出方 | `...::test_every_registered_kind_has_a_producer` |
| 8 | 闸门汇总数与实际夹具数不一致 | 汇总文案分母写死 30/30 | `...::test_ast_gate_count_matches_fixture_total` |
| 9 | 编译期助手报 unbound identifier | `append-pattern/ct` 放在模块顶层，GENERIC 分支在 phase 1 运行 | 模块加载即报错（`racket` require） + `tests/test_cr42_v1_macros.py` |
| 10 | `:pattern` 被 `parse-harness` 拒绝 | 插到了 `:harness` 内部，而 harness 只认 c/v/c 三块 | `parse-harness` 严格匹配 + 端到端编译测试 |
| 11 | 静态模板改坏（括号不平衡） | 批量脚本拼接模板，靠人眼数括号 | `racket` 读入即报 `missing )`；改法改为逐宏 edit + 立即读入校验 |
| 15 | BDD 2 个用例随机失败（`ModuleNotFoundError`） | 我的新测试执行 `sys.path.insert(0, "scripts")`，而 `scripts/tests/` 存在 → `import tests` 被遮蔽，BDD 动态生成测试导入失败 | `...::test_no_global_sys_path_mutation_in_tests`；正解改用 `importlib.util.spec_from_file_location` |
| 17 | 宏展开失败但编译仍然「成功」 | `main.rkt` 对 pattern 宏展开失败只打日志，进程仍返回 0，产物是原式 | **待修**：已登记；当前只在 `tests/test_cr42_sugar_macros.py` 按「stderr 出现 FAIL」断言，退出码语义待单独修复 |
| 16 | triage 把关键信息匿名化 | 归一化把 `No module named 'X'` 的模块名替换成 `'X'`，聚合后看不到缺什么 | `tests/test_triage.py` 断言导入类错误保留引号内容 |

## 二、仅纪律（尚未判据化）

| # | 现象 | 根因 | 为什么暂不判据化 |
|---|---|---|---|
| 12 | 工具调用报语法错 | 我用 TS 模板字面量包 Python/bash 时，反引号与 `${}` 被 JS 抢先解析 | **半自动**：payload 一律用 `write` 落成 `.tmp_*` 再执行，不再内联；配套守护 `test_no_scratch_files_are_tracked` |
| 13 | 覆盖 `write` 已有文件被拒 | 默认策略要求先 `read` 再写 | 工具层策略，无需仓库判据 |
| 18 | 本地全绿、CI 连续 5 轮仍红 | 我用「习惯的命令」验（`pytest tests`），CI 用 `runtime/tests python/tests tests/step_defs tests/patterns`；PATH 有无 racket、装没装 extra 也不同 | **半自动**：`tools/test_paths.txt` 作唯一真源 + 判据 A7；本地跑前先读它 |
| 19 | 编译器整个加载不了（`read-syntax: expected a )`） | 给 `file->value-list` 加 `with-handlers` 时少写一个闭括号 | **自动**：判据 P6（E2E 编译 + `ast.parse`）立刻红 |
| 20 | 判据 P4 由绿转红：宏展开失败仍返回 0 | `had-parse-error?` 定义在使用点之后；Racket 报「不能在定义前引用」，异常被外层吞掉 | **自动**：判据 P4；标记类变量一律定义在文件顶部 |
| 21 | 断言「未捕获异常必须 exit>=4」从未通过 | 断言是未验证的假设；实测 Racket 8.12 以 1 退出，「>=4」是编译器自己的保留档 | **半自动**：写断言前先实测；改为断言 main.rkt 含该档出口 |
| 22 | `uv sync --frozen` 成功但什么都没装 | 先 `touch` 空 `uv.lock` 再 `--frozen`：空 lock 是合法输入，sync 直接跳过 | **自动**：Dockerfile 项目层 `test -x .venv/bin/agentlisp` + 构建期 `agentlisp --help` |
| 23 | Windows 上多路子进程调用解码崩 | `subprocess.run(text=True)` 按 locale(cp1252) 解码 UTF-8 输出 | **自动**：`encoding="utf-8"` 由 codemod 统一（29 处）+ CI 真跑 |
| 24 | 4 条 SRS-ID 长期 ORPHAN | CI 的 pytest 路径漏了 `tests/patterns`，那批用例从未在 CI 跑过 | **自动**：判据 A7（CI 路径必须取自唯一真源） |
| 25 | Windows 上 pytest 报 `file or directory not found: runtime/tests` | 真源文件在 Windows 检出为 CRLF，`tr '\n' ' '` 之后每段路径尾部带 `\r` | **自动**：CI 命令 `tr -d '\r'` + `.gitattributes`（`eol=lf`）+ 判据 A7（只查命令行本身，注释不算） |
| 26 | 判据反验「假通过」：移除代码后仍 PASS | 我把检查写成全文子串匹配，自己刚加的**注释**里也含该字符串 → 条件被注释满足 | **半自动**：反验必须先在脚本里断言「注入生效」，且判据只匹配**目标行**（本轮 A7 已按此改） |
| 27 | Docker 镜像里 `agentlisp: not found`（exit 127） | builder 先 `touch` 空 `uv.lock` 再 `uv sync --frozen`：空 lock 是合法输入，sync「成功但什么都没装」→ 项目层也装不上 → 无 console script | **自动**：Dockerfile 项目层 `test -x .venv/bin/agentlisp` + 构建期 `agentlisp --help` |
| 28 | Build 成功后 `docker run … agentlisp --help` 仍 not found | console script 的 shebang 由 uv 写成**构建期** venv 路径（`/app/python/.venv/bin/python`），运行时镜像只有 `/app/.venv` → execve 失败，sh 报 not found | **自动**：构建期把 shebang 改写为 `/app/.venv/bin/python` 并打印前后值；A8 要求验收走 PATH |
| 29 | 构建期验收「假绿」一轮：真缺陷被回退链掩盖 | 我把验收写成 `PATH → /app/.venv/bin/agentlisp → python -m` 三条依次尝试，第三条成功即算通过 | **自动**：A8（验收命令不得含 `||` 回退、CI 冒烟不得 `|| true`）；验收必须走生产同一条路 |
| 30 | 判据登记表里把 `tools/verify_local.sh` 拼成 `toolls/…` | A2 只比对 ID 集合，不校验表内引用的路径是否存在 → 拼写错误漏过（文档与事实不一致却全绿） | **自动**：A2 已加路径存在性校验（表内反引号路径必须真实存在；切片按标题截断，避免扫到后续章节的绝对路径） |
| 31 | 审查者判定「21 个设计模式仍未落地」 | 他查的是**分发物**（Docker 镜像 / wheel）：镜像只 COPY 了 scheme/python/examples/config/docker，**没有 compiler/** → 分发物确实不能编译 .al；而源码树（含 main）有 28 个宏、AST 闸门 48/48、产物含 self.PATTERNS | **自动**：判据 A9（镜像必须 COPY compiler/ + 构建期真编译一次并断言 self.PATTERNS + README 写明能力边界） |
| 32 | 第三次「判定模式未落地」（代码库审查） | 审查者查的是**发布物**：Latest release 仍是 v2.0.0（2026-10-10，落后 main 75 个提交，`:pattern` 0 处 / `:evolution` 0 处）；分支其实早已合并。同一形态三次现身：旧 main（#18 前）→ 镜像缺 compiler/（#31）→ release 陈旧（本条） | **半自动**：① A9（镜像自证能力）② README 写明能力边界 ③ 本条纪律：判定「是否落地」前先问**我看的是哪一层**——源码树 / git tag / release 资产 / 镜像 / wheel，五层能力并不相同 |
| 14 | 排查慢：先猜后验 | 连续 3 次改判据都没修好，最后才打印原始失败清单 | **半自动**：`scripts/triage.py` 先聚合失败签名 / NFR cell / checker cells；`tests/test_triage.py` 守护解析逻辑 |

## 三、开工前检查（3 条动作，按顺序）

1. **要跑失败分析时**：先执行 `python3 scripts/triage.py [目标]`。看聚合签名，再决定改什么。
   - 同一签名命中 >= 2 次，视为同一根因。先修根因，再整体重跑。
2. **要写多行 payload（Python / Racket / bash）时**：用 `write` 落成 `.tmp_*` 文件再执行。
   - 不要内联进 TS 模板字面量。反引号与 `${}` 会被外层抢先解析。
3. **要改静态模板（quasiquote 列表）时**：逐处单次 edit，每改一处立即用 `racket` 读入校验。
   - 不批量拼接。括号错位靠读入报错定位，比人眼数括号快。

## 四、修订记录

- 2026-10-11：初版。CR-42 期间（P-1…P-5）共记录 14 条，其中 11 条有判据，3 条仅纪律。
- 2026-10-11：第二轮。坑 #12 / #14 降级为「半自动」：新增 `scripts/triage.py` 与
  `tests/test_triage.py`；payload 写法固化为「先落盘再执行」，配套守护
  `test_no_scratch_files_are_tracked`；新增第三节「开工前检查」。仅 #13 仍为纯纪律。
- 2026-10-11：第三轮（清 CI 最后三条红）。新增 #18…#24 共 7 条。
  其中 #18 是本轮**贯穿性**问题：本地验证命令与 CI 不一致，导致「本地绿、CI 红」重复 5 次。
  已改为机器拦：`tools/test_paths.txt` 作唯一真源，CI 与本地都从它取路径，判据 A7 守护。
- 2026-10-12：第五轮（重新发布 v2.1.0，回应代码库审查）。新增 #32。
  审查结论「21 个模式仍未落地」对**发布物**成立（Latest release 停在 v2.0.0，落后 main 75 个提交），
  对源码树不成立。处置：版本 2.0.0→2.1.0（6 处版本源）+ 发布 v2.1.0（GitHub Release + 三平台二进制 + Docker），
  **不发 PyPI**（按既定决策，publish-pypi 改为仓库变量 PUBLISH_PYPI 控制）；
  发布包实查：76 个 .rkt、:pattern 6 处、:evolution 23 处、包内编译产物含 self.PATTERNS。
  同一误判形态已出现三次（旧 main → 镜像缺 compiler/ → release 陈旧），故本次记为纪律条款：
  判定「是否落地」前先声明**看的是哪一层**。
- 2026-10-12：第四轮（追 Docker Build 到绿）。新增 #25…#29 共 5 条。
  * #25 真源文件 CRLF → 路径尾部带 \r；#26 判据反验假通过（被自己注释满足）。
  * #27/#28/#29 是同一形态的三次现身：**安装/入口/验收**三处「看起来成功」。
    共同判据：装完要 `test -x`、入口要跨阶段验证（shebang）、验收要走生产同一条路。
    已落地 A8：验收命令不得含 `||` 回退，CI 冒烟不得 `|| true`。
