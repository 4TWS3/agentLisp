# US-21 / US-22 / US-23 交底：learning / topic-model / a2a 观测留痕

> 基线：ab3fcb0 · 日期：2026-10-14
> 判据（US-21）：学习条目写到产物之外；产物指纹不变
> 判据（US-22）：trace 含分布与命中结果
> 判据（US-23）：trace 含握手状态与 msg_id

---

## 1. 结论

三条都留痕。US-21 写到技能库（产物不动）；US-22 记分布 + 命中；US-23 记握手 + msg_id。

---

## 2. 实现

| 文件 | 改动 |
|---|---|
| runtime/patterns/__init__.py | 新增公共 `record_event`（handler 留痕入口） |
| runtime/patterns/declarative_b3.py | `_B3` 存 harness；`topics` / `send` / `write_back` 各记一条事件 |
| tests/patterns_runtime/test_observability_b3.py | 3 条 |

---

## 3. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 观测三条 | pytest tests/patterns_runtime/test_observability_b3.py | 3 passed |
| 模式全集 | pytest tests/patterns_runtime/ | 314 passed |
| 判据 | python3 tools/standards_check.py | 19 通过 / 0 失败 |

---

## 4. 未做

无（本故事判据范围内的项已全部交付）。
