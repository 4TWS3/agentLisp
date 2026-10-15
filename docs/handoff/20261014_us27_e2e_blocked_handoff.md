# US-27 交底（进行中）：21 条 E2E 的前置与阻塞

> 基线：`fd43f13` · 日期：2026-10-14
> 故事：US-27（作为 M，我要每个接线 kind 有一条 E2E）
> 判据：21 条「编译 → 子进程跑 → 断言」全绿
> 状态：**未完成**。已做前置对齐；发现两处更深阻塞。

---

## 1. 本轮已做：3 处「声明 ≠ 消费」对齐

实测发现注册表 schema 声明的键，与 handler 真读的键不符。

| kind | schema 旧 | handler 真读 | 处置 |
|---|---|---|---|
| `exception` | `backoff real?` | `backoff` 字符串枚举 | 改 `string?` |
| `reflect` | `max-retries` | `reviewer-agent` | 改 `reviewer-agent` |
| `reasoning` | `strategy` | `technique` | 改 `technique` |

验证：`standards_check` 18/0；`test_compiler_end_to_end` + `test_cr42_pattern_language` 32 passed。

---

## 2. 阻塞一：V1 五个宏的产物加载全失败

实测 5 个 V1 夹具。编译通过，但**子进程加载产物时 `on_init` 抛错**：

| 夹具 | 加载报错 |
|---|---|
| defreflect_code_refiner | `reflect 需要 :reviewer-agent` |
| defrouter_ops_gateway | `routes 为必需键` |
| defchain_doc_pipeline | `steps 为必需键` |
| defparallel_multi_search | `branches 为必需键` |
| defplanner_deep_researcher | `plan-size 为必需键` |

**根因**：V1 宏的 `append-pattern`（`compiler/patterns.rkt:96`）只发 `(:pattern :kind K :config (:markers …))`。
handler 要的键在 `plist->blocks` 里被分到 `:multiagent` 桶或 prompt，没进 `:config`。

**含义**：V1 这 5 个 kind 的「接线」只在手工设 `PATTERNS` 的单测里成立。编译路径不成立。

---

## 3. 阻塞二：E2E 的断言素材

21 份契约的「输入」栏有 8 份只写「模式块键：:xxx」，没给完整 `.al`。
E2E 需要每 kind 一份合法 `.al`。可从 `KIND_SLOTS` + handler `validate()` 反推，但要逐 kind 确认。

---

## 4. 判断

US-27 不能独立完成。它依赖：

| 前置 | 归属 |
|---|---|
| V1 五宏把必需键写进 `:pattern :config` | P2-1 接线（US-26）/ P1-1 对齐 |
| 每 kind 一份合法 `.al` | US-27 自身 |

**建议顺序**：先做 US-26（接线）或 P1 余项（US-31/US-11/US-14），再做 US-27。

---

## 5. 未做

- 21 条 E2E 一条未加（现有 1 条只覆盖 priority，走 V2 宏，能加载）。
- V1 五宏未修。
