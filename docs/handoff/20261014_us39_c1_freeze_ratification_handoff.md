# US-39 交底：C1 冻结文件追认（P2-7）

> 基线：93ad36c · 日期：2026-10-14
> 故事：US-39（作为 M，我要 C1 冻结文件追认，以便基线明确）
> 判据：追认 compiler/agentlisp_compiler.rkt

---

## 1. 结论

C1 6 core 建立**追认表**（含 sha256）。改 C1 文件后哈希不符即失败，必须更新追认表 = 追认。

---

## 2. 追认了什么

| 文件 | 状态 |
|---|---|
| compiler/agentlisp_compiler.rkt | 追认：P0 两处（__future__ 位置；build_context 委托基类） |
| compiler/checker.rkt | 追认：US-11 编译期组合校验 |
| compiler/parser.rkt | 未改 |
| compiler/emitter.rkt | 未改 |
| .github/workflows/ci.yml | 未改 |
| pyproject.toml | 未改 |

---

## 3. 为什么这样做

C1 的禁动是「**改动要留痕**」，不是「永不改」。哈希把留痕变成机器拦。

---

## 4. 实现

| 文件 | 作用 |
|---|---|
| docs/spec/c1_freeze_ratification.md | 追认表（6 文件 + sha256 + 原因） |
| scripts/check_c1_freeze.py | 重算哈希，不符即 rc=1 |
| tests/test_c1_freeze.py | 接入门禁 |

---

## 5. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 一致 | python3 scripts/check_c1_freeze.py | OK C1 追认表一致：6 个文件，rc=0 |
| 注入漂移 | 把 parser.rkt 的哈希改成 0 | FAIL 未追认的改动：compiler/parser.rkt，rc=1 |
| 守卫 | pytest tests/test_c1_freeze.py -q --no-cov | 1 passed |

---

## 6. 与故事图 §5 的差异

故事图 §5 曾把 US-39 标为「需人确认基线」。本故事把追认做成**机器记录**：
哈希 + 原因 + 核对脚本。人只需在改 C1 文件时更新表。
