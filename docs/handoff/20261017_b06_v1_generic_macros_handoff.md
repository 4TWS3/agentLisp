# B-06 交底：V1 五宏的 GENERIC 分支可编译

> 判据：非 HC 名的 V1 宏（defrouter/defchain/defparallel/defplanner/...）能编译
> 结果：**已达成**。5 个宏最小参数编译 rc=0。

---

## 1. 结论

修了 4 处，GENERIC 分支现在可用。

---

## 2. 修的 4 处（都在 `compiler/patterns.rkt`）

| # | 症状 | 根因 | 修法 |
|---|---|---|---|
| 1 | `(:tools :tools (import-builtin bash))` 重复键 | 块头键也原样保留 | 块头键 + 列表值 → 按块形状摊开（`block-items`） |
| 2 | `:model-name` 不生效 | 下游只认 `:name` | 分桶时改名 |
| 3 | `缺少必需的 :harness 块` | `ensure-blocks` 的 required 只有 model/tools/context | 加 `:harness`，缺块给可用默认（不再给空块） |
| 4 | `:multiagent` 块被 `:steps` 污染 | pattern 键被分到 `:multiagent` | pattern 键（routes/steps/branches/reducer/planner-prompt）不进块，由 `append-pattern` 收进 `:params` |

`plist->blocks` 与 `plist->blocks/ct` 两份都改了（阶段 0 / 阶段 1 不能共用函数）。

---

## 3. 验证（实测）

| 输入 | 结果 |
|---|---|
| `(defrouter-agent r1 :routes ("a=>b"))` | rc=0，PATTERNS = router/routes |
| `(defchain-agent c1 :steps ("x" "y"))` | rc=0，PATTERNS = chain/steps |
| `(defparallel-agent p1 :branches ("a" "b"))` | rc=0，PATTERNS = parallel/branches |
| `(defplanner-agent pl1 :planner-prompt "拆解")` | rc=0，PATTERNS = planner |
| `(defrouter-agent r2 :model-name "gpt-x" :routes ...)` | rc=0，model_config.provider=openai、name=gpt-x、system_prompt 非空 |

`pytest tests/test_v1_generic_macros.py tests/patterns` → **139 passed**。

---

## 4. 未做

- 只验了 4 个宏；`defreflect-agent` 与 `defmemory-agent` 未加用例。
- 默认模型硬编码 `openai/gpt-5.6`（与 HC 分支一致）；换成别的需要用户显式给 ```:provider``` / ``:name`。
