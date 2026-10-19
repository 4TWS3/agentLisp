# 复刻 spec-writer：F-AMS-1 放宽（条件边成环合法）

> 日期：2026-10-18
> 场景：用 agentLisp 复刻 bigdipper/agents/spec-writer

---

## 1. 结论

复刻时撞到 F-AMS-1 的硬限制：**它禁一切环**，而 spec-writer 的 5 个环全由条件边构成。

已改为：**无条件边成环才失败；条件边成环只告警。**

---

## 2. 为什么这样改是对的

| 边的类型 | 能否打断环 | 判定 |
|---|---|---|
| `edge` / `sequential` | 不能（没有判定） | 成环 = 真 bug → **编译失败** |
| `conditional-edge` | 能（路由函数决定） | 成环 = 作者显式声明 → **告警** |

条件环仍然要**看得见**：编译时打一条 `[WARN]`，说明退出靠 LangGraph 的 `recursion_limit` 兜底。

---

## 3. spec-writer 的 5 个环（全部条件边）

```
create_missing_foundation -> scan_knowledge_base
confirm_clarify -> confirm_clarify
review -> draft
gm_qa -> gm_review
revise -> review
```

原版用 LangGraph，天然允许；agentLisp 现在也能表达了。

---

## 4. 改动

| 文件 | 改动 |
|---|---|
| `compiler/agentlisp_compiler.rkt` | 环判定只看非 conditional-edge 的边；条件环打 eprintf 告警 |
| `tests/test_cr43_workflow.py` | 新增「条件边成环合法」用例；原「无条件成环失败」用例保留通过 |
| C1 追认表 | 新哈希 |

---

## 5. 验证

| 项 | 结果 |
|---|---|
| `pytest tests/test_cr43_workflow.py` | 10 passed |
| 复刻项目编译 | rc=0，5 条条件环告警 |
| 复刻项目全流程 | 4 次中断 + 终稿 + OA 方案 |
