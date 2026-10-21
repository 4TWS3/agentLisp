# agentLisp 一页速查

## 最小可跑

```bash
python3 scripts/al_new.py /tmp/demo && cd /tmp/demo && python3 run.py
```

## 五个必填块

| 块 | 作用 |
|---|---|
| `:model` | 模型：provider / name / system-prompt |
| `:tools` | 工具：import-builtin / define-tool |
| `:context` | 记忆策略 |
| `:harness` | 护栏三块：constrain / verify / correct |
| `:workflow` | 节点图 |

## 可选块

| 块 | 作用 |
|---|---|
| `:state` | 状态字段（含 :type / :default / :reducer） |
| `:lisp` | 辅助函数 |
| `:macro` | 宏（可多次） |
| `:pattern` | 模式（可多次） |
| `:evolution` | 演化契约 |
| `:multiagent` | 多 agent（与 :workflow 互斥） |

## 节点体六种写法

| 用途 | 写法 |
|---|---|
| 纯计算 | `:body (hash "out" (+ 1 2))` |
| 调模型 | `:body (hash "out" (llm "提示词"))` |
| 调宿主 | `:body (hash "out" (py/call "json.loads" raw))` |
| 人工中断 | `:body (hash "out" (interrupt (hash "node" "x")))` |
| 并行扇出 | `:body (hash "out" (fanout items fn))` |
| 循环 | `(loop ((i 0)) (if (< i n) (recur (+ i 1)) i))` |

**逃逸口**：`:handler "模块.函数"` 会**编译期告警**，产物标 `escaped: True`。

## 枚举

| 枚举 | 取值 |
|---|---|
| 节点类型 | agent / computation / evaluator / subagent |
| 拓扑 | sequential / edge / conditional-edge / conditional-loop |
| 效应 | pure / revertible / non_revertible |
| 状态类型 | dict / str / int / float / bool / list |
| reducer | merge（dict）/ append（list）/ sum（数字） |
| provider | anthropic / openai / qwen / mock |
| 记忆层 | L0-Abstract / L1-Overview / L2-FullText |

## 报错

编译失败会打三行：

```
原因: 节点声明的输出字段没有在 (:state :fields …) 里登记。
怎么改: 在 (:state :fields ((字段 :type 类型))) 里补上该字段。
例子:
    (:state :fields ((draft :type str)))
```

42 条提示见 `docs/llm/errors.json`。

## 查语言特性

`docs/llm/al_catalog.json`（从编译器生成，漂移即 CI 红）。
