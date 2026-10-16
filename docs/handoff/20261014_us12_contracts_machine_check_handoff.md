# US-12 交底：21 份契约的机器校验（P1-4 / B5）

> 基线：7ad8c9d · 日期：2026-10-14
> 故事：US-12（作为 D，我要看 21 份契约的机器校验结果）
> 判据：六栏齐备 + 被测试引用，有脚本可跑

---

## 1. 结论

一键报告：**21/21 栏位齐备 + 被测试引用**。

---

## 2. 复用判断，不复制

| 项 | 判断实现 |
|---|---|
| 栏位齐备 | tools/standards_check.py 的 _contract_columns_problems（A12） |
| 被测试引用 | 扫 tests/ 是否引用 CT-KIND-01（A11 同一判据） |
| 引擎消费 | runtime.patterns.KIND_SLOTS |

---

## 3. 交付

| 文件 | 作用 |
|---|---|
| scripts/check_contracts.py | 一键报告（21 行） |
| tests/test_contracts_report.py | 接入门禁 |

---

## 4. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 报告 | python3 scripts/check_contracts.py | OK 21/21，rc=0 |
| 守卫 | pytest tests/test_contracts_report.py | 1 passed |
| 判据 | python3 tools/standards_check.py | 18 通过 / 0 失败 |

---

## 5. 与故事的差异

故事图把 US-12 当独立新工作。实际：A11（契约 + 测试 + id 引用）与 A12（栏位）已在 US-33 / US-30 落地。
本故事只加「一键报告 + 守卫」，把散在两条判据里的结果汇到一处。
