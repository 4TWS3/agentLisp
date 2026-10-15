# US-11 交底：模式组合校验升编译期（F-AMS-4 / P1-3）

> 基线：`3f4a1fe` · 日期：2026-10-14
> 故事：US-11（作为 D，我要模式组合错误被编译期拒，以便不静默失活）
> 判据：同组两 kind / 缺依赖 → rc=1

---

## 1. 结论

**互斥组校验已从运行期升到编译期。** 同组两 kind → 编译期失败，点名双方（实测）。

---

## 2. 为什么

F-AMS-4 原文：agentLisp 现有 `GROUPS`（互斥组）在**运行期 `on_init`** 才报错。**这是错的时机。**
用户装了产物、跑到加载才失败。编译期失败更早、更清楚。

---

## 3. 实现

| 文件 | 改动 |
|---|---|
| `compiler/pattern_registry.rkt` | 新增 `pattern-groups` / `pattern-requires` / `composition-errors` |
| `compiler/checker.rkt` | `check-patterns` 收集 kinds，调 `composition-errors`，raise `ERR_PATTERN_CONFLICT` |
| `runtime/patterns/__init__.py` | `GROUPS` 保留（运行期防御，不删） |
| `tests/test_cr42_pattern_composition.py` | 3 条：同组失败 / 跨组通过 / 两组数据同源 |

---

## 4. 判据覆盖

| 判据 | 状态 |
|---|---|
| 同组两 kind → 编译期失败，点名双方 | **已做** |
| A 要求 B 而 B 缺失 → 编译期失败 | **机制在位，关系表为空** |
| 蕴含：自动补齐 + 产物记录 + warn | **未做** |

---

## 5. 未做：requires / implies 图（诚实登记）

F-AMS-4 要三类关系：互斥 / 要求 / 蕴含。仓库只定义了「互斥组」（设计 v2 §6）。
**没有任何 kind→kind 的 requires/implies 关系被定义过。我不发明需求。**

现状：`pattern-requires` 是空表。机制（`composition-errors` 的 missing 分支）在位，
定义关系即生效。定义关系需要领域输入。

---

## 6. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 同组 | 编译 chain + router | rc≠0：`ERR_PATTERN_CONFLICT: 模式冲突：chain、router 同属「编排」组` |
| 跨组 | 编译 chain + fsm | rc=0 |
| 同源 | 比对 Racket `pattern-groups` 与 Python `GROUPS` | 相等 |
| 相关测试 | `pytest` 组合 + 冲突矩阵 | 217 passed |
| 判据 | `python3 tools/standards_check.py` | 18 通过 / 0 失败 |
