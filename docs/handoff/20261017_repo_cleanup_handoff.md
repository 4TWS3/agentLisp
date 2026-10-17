# 仓库清理（2026-10-17）

> 触发：用户问「代码仓库是否需要清理掉没用的文档、代码」

---

## 1. 清理了什么

| 项 | 处理 | 理由 |
|---|---|---|
| `emit-multi-class-vars`（compiler） | **删除** | D2 内聚后它产出的 `_multi_topology/_multi_workers` 已不存在，函数无调用者 |
| `.tmp_build/` / `dist/` | **删除** | 本地构建产物（本就被 gitignore / .git/info/exclude 忽略） |

---

## 2. 明确保留及理由

| 项 | 保留理由 |
|---|---|
| `docs/handoff/` 52 份 | 每条故事的审计轨迹。删了就无法追溯「为什么这么做」 |
| `docs/plans/` 11 份 | 主线计划 + 本轮建立的跟踪表（remaining-stories / pattern-overhead / backlog） |
| `python/` + `scheme/` | 旧 v0.1 兼容目录（README 写明保留） |
| `scripts/check_handoff_compliance.py` | 未接 CI 的手工检查器；不是死代码，是没接线 |
| `PatternRuntime.after_turn` | 无生产调用者（US-30 已把它从槽位移除），但仍是公开 API 且测试在用。**登记为待定，不在本轮删** |

---

## 3. 未做的清理（有意）

- 未删任何 handoff：项目约定「一次改动一份交底」。
- 未删 `after_turn`：删它要动公开 API，收益小于风险。
- 未动 `tools/fix_silent_excepts.py`：手工 codemod，按需使用。

---

## 4. 验证

| 项 | 结果 |
|---|---|
| `racket -e '(require ...agentlisp_compiler)'` | load ok |
| C1 追认 | OK 6 文件 |
| 编译器 / 宏 / 多 agent 测试 | 35 passed |
| ruff | 全过 |
