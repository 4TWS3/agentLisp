# US-37 交底：v2.3.1 补丁（P5-1 / B8）

> 基线：a5f69aa · 日期：2026-10-14
> 故事：US-37（作为 A，我要制品不含已知不可用项，以便可发布）
> 判据：v2.3.1 打补丁；v2.3.0 标不可用

---

## 1. 结论

版本 2.3.0 → 2.3.1（6 处）。README 标注 v2.3.0 **已知不可用**。

---

## 2. 修了什么

| 缺陷 | 修复 |
|---|---|
| 带模式的产物无法 import（__future__ 位置错） | P0-1（e06b030） |
| 产物 build_context 漏模式注入 | P0-1（e06b030） |

---

## 3. 改动

| 文件 | 改动 |
|---|---|
| pyproject.toml / runtime/__init__.py / host/gateway.py / host/gateway_sse.py（2 处）/ compiler/main.rkt | 2.3.0 → 2.3.1 |
| README.md | 顶部改 v2.3.1；标注 v2.3.0 已知不可用 |
| runtime/tests/test_cli_if_cli_1_exit_encoding.py | 版本断言改用单一真源 |
| tests/test_version_consistency.py | 新增：5 处版本一致 |
| docs/spec/c1_freeze_ratification.md | pyproject 哈希追认（C1 文件） |

---

## 4. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 版本一致 | pytest tests/test_version_consistency.py | 3 passed |
| CLI | pytest runtime/tests/test_cli_if_cli_1_exit_encoding.py | 1 passed |
| C1 | python3 scripts/check_c1_freeze.py | OK 6 个文件 |
| E2E | pytest tests/patterns_runtime/test_e2e_all_kinds.py | 21 passed |
| 判据 | python3 tools/standards_check.py | 18 通过 / 0 失败 |

---

## 5. 未做

- 未实际发版（P5-2）。硬顺序：P5-3 真实环境验收（需 API key）→ P5-2。
- GitHub release tag / docker tag 未打（需 CI）。
