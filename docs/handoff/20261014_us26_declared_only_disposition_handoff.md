# US-26 交底：8 个仅声明 kind 定性（P2-1）

> 基线：`ce59dec` · 日期：2026-10-14
> 故事：US-26（作为 M，我要 8 个仅声明 kind 完成接线，以便承诺兑现）
> 故事图判据：引擎消费数 13 → 21
> 实际：**未接线**。本故事交付「定性」（P2-1 允许的第二态）。

---

## 1. 结论

8 个 kind 逐个定性为**声明层**，并给理由。判据 G2「无第三态」机器可核对。

---

## 2. 为什么不接线（顺序约束）

接线需要编排器（F-AMS-7 / P4-1）。主计划把编排放在 **P4**，依赖顺序在 P2 之后。
在 P2 硬做接线 = 跳过依赖顺序。

P4-2 会把其中 5 个接线：router / chain / parallel / planner / decomposition。

---

## 3. 定性表

| kind | 定性 | 理由 |
|---|---|---|
| router | 待 P4 | F-AMS-7 select_next；引擎目前不按 kind 选下一动作 |
| chain | 待 P4 | 步骤顺序由编排器驱动 |
| parallel | 待 P4 | 扇出/归并由编排器驱动 |
| planner | 待 P4 | 先出计划再执行由编排器驱动 |
| decomposition | 待 P4 | 递归分解与 :multiagent 协调 |
| topic-model | 声明层 | 聚类结果无引擎消费点 |
| a2a | 声明层 | 跨 Agent 消息无引擎消费点 |
| learning | 声明层 | 写回技能层无引擎消费点 |

---

## 4. 实现

| 文件 | 改动 |
|---|---|
| `runtime/patterns/__init__.py` | 新增 `DECLARED_ONLY_REASON`（8 条） |
| `scripts/check_slot_model.py` | 要求键集 == DECLARED_ONLY 且理由非空 |
| `tests/test_slot_model.py` | 加 2 条守卫（缺定性 / 定性为空） |

---

## 5. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 一致 | `python3 scripts/check_slot_model.py` | `OK 槽位模型：… DECLARED_ONLY=8`，rc=0 |
| 守卫 | `pytest tests/test_slot_model.py -q --no-cov` | 6 passed |
| 判据 | `python3 tools/standards_check.py` | 18 通过 / 0 失败 |

---

## 6. 偏离故事图判据（诚实登记）

故事图 US-26 写「引擎消费数 13 → 21」。本故事**未达到**。

理由：接线依赖 P4-1 编排器；主计划顺序 P2 → P3 → P4。
已记入 `docs/plans/backlog-out-of-map.md` B-07，待 P4 完成后回填。
