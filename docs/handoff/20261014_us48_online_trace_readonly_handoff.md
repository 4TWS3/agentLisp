# US-48 交底：在线循环只读（FR-EVO-3）

> 基线：cd7604a · 日期：2026-10-14
> 判据：断言产物未被写

---

## 1. 结论

`:online-trace #t` 从语法到产物到运行期打通。元数据写到产物外，源码不动。

---

## 2. 实现

| 层 | 改动 |
|---|---|
| 编译期 | `parse-evolution` 接受可选首属性 `(:online-trace #t|#f)`；产物 `EVOLUTION` 含 `online_trace` |
| 运行期 | `_write_online_trace()` 在 `run()` 的 finally 写元数据 JSON 到 `$AGENTLISP_ONLINE_TRACE_DIR` |
| 只读保证 | 写路径只碰 trace 目录；测试断言 `.al` 哈希不变 |

---

## 3. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 只读 | pytest runtime/tests/test_online_trace.py | 2 passed |
| 编译 | 带 `(:online-trace #t)` 编译 | 产物含 `'online_trace': True` |
| 回归 | pytest runtime/tests/test_harness_v2.py | 38 passed |

---

## 4. 未做

- `:offline-evolver` 属性仍未解析（US-49/US-50 会用）。
- 规格的 keyword 形式（`:mutation-targets` 直接做 keyword）仍未支持（US-47 对齐项）。
