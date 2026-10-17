# US-53 交底：节点声明效应等级（F-AMS-8）

> 基线：cb61d09 · 日期：2026-10-14
> 判据：节点可声明 :effect；non_revertible 在并发中必须串行

---

## 1. 结论

`:effect` 三档（pure / revertible / non_revertible）落地。
`non_revertible` 节点与 `:pattern parallel` 并存 -> 编译期失败（必须串行）。

---

## 2. 实现

| 项 | 内容 |
|---|---|
| 节点字段 | `:effect`（默认 `pure`；枚举封闭） |
| 编译期拦 | `non_revertible` 节点 + `:pattern parallel` -> 失败，点名节点 |
| 产物 | `WORKFLOW.nodes[].effect` |

「并发」的判据用 `:pattern parallel`（当前唯一的并发构造）。这是本轮的口径选择，已写明。

---

## 3. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 效应声明 | pytest tests/test_cr43_effect.py | 3 passed |
| 正例 | non_revertible 无 parallel | 编译通过，产物 effect=non_revertible |
| 反例 | non_revertible + parallel | rc≠0，含「必须串行」 |

---

## 4. 未做

- 不做自动回滚（F-AMS-8 明确：没有事务语义，只做声明）。
- 未定义 `:effect` 在运行期的调度效果（当前只做编译期拦）。
