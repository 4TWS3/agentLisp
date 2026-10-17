# C1 冻结文件追认（US-39 / P2-7）

> 基线：93ad36c · 日期：2026-10-14
> 范围：CR-41 的「C1 6 core」。这些文件默认禁动。
> 规则：改动任一 C1 文件，必须在本表更新哈希并写清原因（= 追认）。
> 机器核对：python3 scripts/check_c1_freeze.py（哈希不符即未追认）。

---

## 1. 追认表

| 文件 | sha256 | 状态 |
|---|---|---|
| compiler/checker.rkt | c205f8efd5867eb345c1ddd19cca397b6265cb868d0f6850332818321bf1aa82 | 追认：US-11 加编译期组合校验（check-patterns 调 composition-errors） |
| compiler/parser.rkt | eaeb130d495163434ce3bdeeddf15aca930c3d51fd6bc4130a59051cb46375c2 | 未改 |
| compiler/emitter.rkt | 369816cfb7ed03a189e315589bcd1b74666bf227f7e422dfb2ac9229722db0a9 | 未改 |
| compiler/agentlisp_compiler.rkt | 143fe75b54536bfc3876478af615921ba639fcddd85e4d935ce28af83e9c922f | 追认：P0；US-04~10 :state/:workflow；US-48 :online-trace；US-53 :effect；US-47 规格对齐；US-06 D2 内聚（subagent） |
| .github/workflows/ci.yml | 8872af2347a15428d34ab085f67b5d6d82ffe2aa33ed8bcb5aa291b266b8cb2b | 未改 |
| pyproject.toml | 5d2042bc362477bf6c2c183cc7dcc1c50180c2b52bea2869142696d58b82ed9a | 追认：US-37 版本；US-01 删坏 entry point；v2.3.2 版本号 |

---

## 2. 怎么用

1. 改任一 C1 文件。
2. 跑 python3 scripts/check_c1_freeze.py。它报哪个文件的哈希不符。
3. 把该文件的新哈希写回本表，并在「状态」列写清原因。这叫追认。

为什么要这么做：C1 的禁动是「改动要留痕」，不是「永不改」。哈希把留痕变成机器拦。
