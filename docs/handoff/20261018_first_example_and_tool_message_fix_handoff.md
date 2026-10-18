# 第一个可跑示例 + 两个真缺陷

> 日期：2026-10-18
> 目标：从零做一个示例，边做边暴露问题

---

## 1. 结论

示例跑通了（Mock 与真模型都通）。过程中打出**两个真缺陷**，都已修。

---

## 2. 示例

| 文件 | 作用 |
|---|---|
| `examples/first-agent.al` | DSL 源码：命令行助手，声明用 bash |
| `examples/first_agent_run.py` | 跑法：注入工具注册表 + 选 Mock / 真模型 |
| `examples/dist/first_agent.py` | 编译产物（`FirstAgentHarness`） |

跑法：

```bash
racket compiler/main.rkt -i examples/first-agent.al -o examples/dist/first_agent.py
python examples/first_agent_run.py            # Mock
OPENAI_BASE_URL=http://127.0.0.1:11434/v1 python examples/first_agent_run.py --real
```

实测输出：

| 模式 | status | final |
|---|---|---|
| Mock | success | `OK, done.` |
| 真模型（qwen3:4b） | success | `955`（= 仓库里 .py 文件真实数量） |

---

## 3. 缺陷 1：工具消息 content 是 dict（P0）

**现象**：真模型第一轮出 tool_call 后，第二轮请求 400。
```
invalid message content type: map[string]interface {}
```

**根因**：`base_harness_v2` 把 observation（dict）直接当 `role="tool"` 的 content。

**为什么测试没抓到**：MockLLMClient 不出 tool_calls，永远走不到第二条消息。

**修法**：dict/list 一律 `json.dumps` 成字符串。

---

## 4. 缺陷 2：工具参数可能是 JSON 字符串

**现象**：自定义 client 回 OpenAI 原始形状（`arguments` 是字符串）时，
`constrain` 里 `args.get(...)` 抛 `AttributeError: 'str' object has no attribute 'get'`。

**修法**：两种形状都收——字符串就 `json.loads`，dict 直接用。

---

## 5. 验证

| 项 | 命令 | 结果 |
|---|---|---|
| 回归测试 | `pytest tests/test_tool_message_content_is_str.py` | 1 passed |
| Mock 跑通 | `python examples/first_agent_run.py` | success |
| 真模型跑通 | `... --real` | success，答案 = 真实文件数 |

---

## 6. 未做（新登记）

| 项 | 说明 |
|---|---|
| `:tools` 不自动接线 | 产物只带 `tools_config`，bash 等实现要调用方注入。示例里手写了 20 行注册表 |
| 内置工具库 | 没有 `import-builtin bash` 的现成实现，需自己写 |
