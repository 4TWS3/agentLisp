# US-31 交底：防膨胀规则（P1-2 / 决策 D3）

> 基线：`3c4c34f` · 日期：2026-10-14
> 故事：US-31（作为 M，我要防膨胀规则，以便槽位表不变能力清单）
> 判据：新增槽位必须同时新增调用点 + 断言

---

## 1. 结论

防膨胀规则入判据。只加槽位、不加运行时调用点 → 失败（实测）。

---

## 2. 规则（D3 原文）

> 槽位只能由运行时的调用点定义。新增槽位 = 新增一个真实调用点 + 一条断言。
> 禁止先加槽位再加实现。

---

## 3. 实现

`scripts/check_slot_model.py` 的 `check()` 改为可注入参数，新增两条防膨胀判据：

| 判据 | 含义 |
|---|---|
| 已实现槽位必须一一有调用点证据 | `SLOTS - PENDING` 与 `SLOT_EVIDENCE` 的键集合必须相等 |
| 证据不得含未声明的槽位 | 反向检查，防「加证据不加槽位」 |

`tests/test_slot_model.py` 加 3 条守卫，证明「能拦住」：

1. 加一个 ghost 槽位（无证据）→ 失败。
2. kind 声明 SLOTS 之外的槽位 → 失败。
3. 调用点证据在 runtime 找不到 → 失败。

---

## 4. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 当前一致 | `python3 scripts/check_slot_model.py` | `OK 槽位模型：… SLOTS=8`，rc=0 |
| 守卫 | `pytest tests/test_slot_model.py -q --no-cov` | 4 passed |
| 相关三文件 | `pytest tests/test_slot_model.py tests/test_standards.py tests/test_contract_columns.py` | 11 passed |

---

## 5. 与 US-30 的边界

| 故事 | 交付 |
|---|---|
| US-30 | 立模型：SLOTS / KIND_SLOTS / LANDED / DECLARED_ONLY |
| US-31 | 立防膨胀判据 + 守卫（证明能拦住） |

---

## 6. 未做

- 产物 PATTERNS 仍未带 `slots` 字段（F-AMS-6 的「产物声明」半）。见 US-30 交底 §6。
- 「槽位数 == 调用点数」按「每槽位至少一个调用点」核，不作字面强等（`budget` 覆盖两个调用点）。
