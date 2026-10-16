# US-08 / US-10 交底：节点级插值 + 字段可达性（F-AMS-5 / F-AMS-3）

> 基线：25a58d2 · 日期：2026-10-14
> 判据（US-08）：{field} 只允许在 :dynamic；未知字段编译期拒
> 判据（US-10）：读未声明字段 -> rc=1；只写不读 -> 警告

---

## 1. 结论

节点可声明 `:prompt (:static … :dynamic …)` 与 `:output-fields`。
插值只准进 `:dynamic`；未知字段编译期拒。字段可达性给警告。

---

## 2. 实现

| 规则 | 判据 | 时机 |
|---|---|---|
| R1 | `:static` 段含 `{field}` -> 失败 | 编译期 |
| R2 | `:prompt` 拆 `:static` / `:dynamic` | 编译期 |
| R3/R4 | `:dynamic` 的 `{field}` 必须是 `:state` 已声明字段 | 编译期 |
| US-10 | 只写不读 -> 警告；无人读写 -> 警告；读但无写且无默认 -> 失败 | 编译期 |

---

## 3. 发现的问题（B-10）

Racket 的 `log-warning` **默认不显示**（要 `PLTSTDERR`）。那等于静默降级。
已把本故事的警告改用 `eprintf`。
**既有 `compiler/checker.rkt:666` 的 `log-warning` 有同样问题。** 记 backlog B-10。

---

## 4. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| US-08 / US-10 | pytest tests/test_cr43_interpolation.py | 5 passed |
| 状态 + 工作流 + 插值 | pytest tests/test_cr43_*.py | 19 passed |

---

## 5. 未做（诚实登记）

- 上游顺序的精确可达性。当前按「全图有无写者」判，比 F-AMS-3 的「上游节点」宽松。
