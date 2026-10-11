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

## 二、仅纪律（尚未判据化）

| # | 现象 | 根因 | 为什么暂不判据化 |
|---|---|---|---|
| 12 | 工具调用报语法错 | 我用 TS 模板字面量包 Python/bash 时，反引号与 `${}` 被 JS 抢先解析 | 属我自己的工具用法，不进仓库；规避法：改用 `chr(96)` 拼反引号、bash 变量写 `\${k}` |
| 13 | 覆盖 `write` 已有文件被拒 | 默认策略要求先 `read` 再写 | 工具层策略，无需仓库判据 |
| 14 | 排查慢：先猜后验 | 连续 3 次改判据都没修好，最后才打印原始失败清单 | 已改为「先取证再改」；行为判据无法自动断言，靠流程纪律 |

## 三、修订记录

- 2026-10-11：初版。CR-42 期间（P-1…P-5）共记录 14 条，其中 11 条有判据，3 条仅纪律。
