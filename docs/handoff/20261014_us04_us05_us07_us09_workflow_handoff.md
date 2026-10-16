# US-04 / US-05 / US-07 / US-09 交底：状态字段 + 工作流图（F-AMS-1/2/3）

> 基线：25a58d2 · 日期：2026-10-14
> 故事：US-04 状态字段 / US-05 工作流图 / US-07 确定性节点 / US-09 非法工作流编译期拒

---

## 1. 结论

四个故事一起交付。新增两个语言构造：`(:state :fields …)` 与 `(:workflow …)`。
编译期拦：引用不存在节点 / 入口未声明 / 节点不可达 / 未声明环 / `:workflow` 与 `:multiagent` 并存 / `:handler` 格式错 / computation 缺 handler。

---

## 2. 交付

| 故事 | 产物 | 判据 |
|---|---|---|
| US-04 | `self.STATE_FIELDS` | 声明后产物含字段表 |
| US-05 | `self.WORKFLOW`（entry + nodes + edges + loops） | 4 类拓扑；节点与边可读 |
| US-07 | `:handler` 格式校验 | `模块.函数` / `模块.类.方法`；computation 必填 |
| US-09 | 编译期校验 | 引用/入口/可达/环 四类失败，rc=1 |

**4 类拓扑**：sequential / edge / conditional-edge / conditional-loop。

---

## 3. 改动

| 文件 | 改动 |
|---|---|
| compiler/agentlisp_compiler.rkt | parse-state / parse-workflow / 可达与环检测 / emit-state-dict / emit-workflow-dict；partition-blocks 收 :state 与 :workflow |
| tests/test_cr43_state_fields.py | 5 条（正例 + 4 负例） |
| tests/test_cr43_workflow.py | 9 条（正例 + 8 负例） |

---

## 4. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 状态字段 | pytest tests/test_cr43_state_fields.py | 5 passed |
| 工作流 | pytest tests/test_cr43_workflow.py | 9 passed |

---

## 5. 未做

- US-08（节点级提示插值 `{field}`）：未做，见下一步。
- US-06（`defmultiagent` 与等价 `:workflow` 产物一致）：未做。
- US-10（状态字段可达性：读未声明 / 只写不读）：未做。
- 运行期不消费 WORKFLOW（US-19 编排接线才消费）。
