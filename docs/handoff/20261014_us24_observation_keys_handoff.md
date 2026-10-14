# US-24 交底：观察值键用户文档（含机器核对）

> 基线：`d21112a` · 日期：2026-10-14
> 故事：US-24（作为 O，我要观察值键有文档，以便自己读懂 trace）
> 判据：6 个键有用户可见说明（实测 runtime 读 **14** 个键名）

---

## 1. 结论

用户文档已写，覆盖 runtime 真读的**全部 14 个键名**。核对脚本接进门禁。

---

## 2. 键从哪来（实证，不猜）

唯一真源 = `runtime/` 里 `observation.get("k")` / `observation["k"]` 的读取点。

| 类别 | 键 | 读取点 |
|---|---|---|
| 工具结果 | `exit_code` / `stdout` / `stderr` / `error` | `base_harness_v2.verify` / 轨迹记录 |
| 模式观察门 | `answer` / `final_answer` / `evidence_ids` / `fields` / `payload` / `score` / `reviewer` / `audit` / `reasoning` / `progress` | `patterns/__init__.py` `verify_observation` |

---

## 3. 交付

| 文件 | 作用 |
|---|---|
| `docs/spec/agentlisp_observation_keys.md` | 用户文档（键总表 + 来源 + 常见误读） |
| `scripts/check_observation_keys_doc.py` | 核对：代码读的键必须在文档里 |
| `tests/test_observation_keys_doc.py` | 接入 pytest / 门禁 |
| `README.md` | 顶部加 ⑤ 链接 |

---

## 4. 判据数字的偏差（记录，不改判据）

故事图写「6 个键」。实测 14 个键名（12 概念 + 2 别名）。
本故事按 14 交付，多于判据。故事图数字记入 `docs/plans/backlog-out-of-map.md` B-04。

---

## 5. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 覆盖 | `python3 scripts/check_observation_keys_doc.py` | `OK 文档覆盖全部观察值键：14 个`，rc=0 |
| 注入漂移 | 把 `reviewer` 改成 `reviewer_typo` | `FAIL 文档缺这些观察值键：['reviewer']`，rc=1 |
| 守卫 | `pytest tests/test_observation_keys_doc.py -q --no-cov` | 1 passed |

---

## 6. 未做

- 未改 runtime 行为。只写文档 + 核对。
- 未做「去掉 verify_observation 的 kind 字符串分派」（原清单 #6）。那归 P1-1 槽位重构。
