# US-47 交底：RSI 规格与实现对齐（六处不符）

> 基线：cb61d09 · 日期：2026-10-14
> 判据：六处不符逐条修正

---

## 1. 六处不符（修前实测）

| # | 规格（RSI §3.1 / FR-EVO） | 实现（修前） | 修后 |
|---|---|---|---|
| 1 | TargetSymbol 含 `prompt-patches` | 枚举缺 | 补上 |
| 2 | InvariantSymbol 含 `model-provider` | 枚举缺 | 补上 |
| 3 | `:offline-evolver String` | 不解析 | 解析并 emit `offline_evolver` |
| 4 | `:verifier-gate (:suite "名" …)` | 只收裸名 `"名"` | 两种都收 |
| 5 | FR-EVO-2：侵入不变量抛 `ERR_IMMUTABLE_INVARIANT_VIOLATION` | 未实现 | 实现（原符号重叠即抛） |
| 6 | 语法是 keyword 形式（`:mutation-targets (skills …)`） | 只有位置形式 | 两种都收（向后兼容） |

**另外**：规格指定的测试文件 `compiler/tests/test_evolution.rkt` 与 `test_checker_evolution.rkt` 不存在。已创建。

---

## 2. 实现

| 文件 | 改动 |
|---|---|
| compiler/agentlisp_compiler.rkt | 枚举补两项；`parse-evolution` 双形式；`:offline-evolver`；`:suite`；`ERR_IMMUTABLE_INVARIANT_VIOLATION`；emit `offline_evolver` |
| compiler/tests/test_evolution.rkt | FR-EVO-1（keyword + 位置两形式） |
| compiler/tests/test_checker_evolution.rkt | FR-EVO-2（侵入抛出 + 不重叠不抛） |

---

## 3. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| FR-EVO-1/2 | raco test compiler/tests/test_evolution.rkt test_checker_evolution.rkt | 4 tests passed |
| Python 侧 | pytest tests/test_cr42_evolution.py tests/test_evolution_consumption.py | 10 passed |
| 六字段产物 | 编译 keyword 形式 | `online_trace/offline_evolver/mutation_targets/immutable_invariants/verifier_gate` 齐全 |

---

## 4. 未做

- 规格的 `:online-trace` 仍要求「完整写入元数据」；元数据字段见 US-48，本轮未扩字段。
- 未把 SRS 的 FR-EVO 表格路径从「待建」改为「已建」（表格只写路径，不写状态）。
