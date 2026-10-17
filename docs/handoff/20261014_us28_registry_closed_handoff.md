# US-28 交底：孤儿条目收口（P2-2 / B2）

> 基线：`5ebb9cd` · 日期：2026-10-14
> 故事：US-28（作为 M，我要 2 个孤儿条目收口，以便注册表无悬空）
> 判据：`memory` / `multi-agent`：接线或登记为声明层

---

## 1. 结论

2 个孤儿登记为**非运行期 kind**，并给理由。
注册表 **23 = 运行期 21 + 非运行期 2**。机器核对。

---

## 2. 为什么不接线

| kind | 语义承载者 |
|---|---|
| `memory` | `(:context :memory-policy …)` 核心语法 |
| `multi-agent` | `(:multiagent :topology … :workers …)` 核心语法 |

两者都不需要模式槽位。硬接线会造出**第二个消费点**（违反 A1）。

---

## 3. 实现

| 文件 | 改动 |
|---|---|
| `runtime/patterns/__init__.py` | 新增 `NON_RUNTIME_KINDS`（2 条） |
| `tests/test_cr42_registry_closed.py` | 3 条：注册表 = 运行期 + 非运行期；handler 无悬空；理由非空 |

---

## 4. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 注册表闭合 | `pytest tests/test_cr42_registry_closed.py -q --no-cov` | 3 passed |
| 判据 | `python3 tools/standards_check.py` | 18 通过 / 0 失败 |

---

## 5. 未做

无（本故事判据范围内的项已全部交付）。
