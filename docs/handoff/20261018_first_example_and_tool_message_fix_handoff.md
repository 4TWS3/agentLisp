# 第一个示例跑通（DeepSeek）+ 三个真缺陷

> 日期：2026-10-18
> 目标：用真模型跑通一个端到端示例

---

## 1. 结论

示例跑通：DeepSeek `deepseek-v4-flash` → 真调 bash → 答案 **955**（= 仓库 .py 真实数量）。

过程中打出 **3 个真缺陷**，全部已修。前两个是 Mock 测试永远碰不到的。

---

## 2. 示例

| 文件 | 作用 |
|---|---|
| `examples/first-agent.al` | DSL：命令行助手，声明用 bash |
| `examples/first_agent_run.py` | 三种模式：Mock / `--real`(Ollama) / `--deepseek` |
| `examples/dist/first_agent.py` | 编译产物 |

```bash
racket compiler/main.rkt -i examples/first-agent.al -o examples/dist/first_agent.py
DEEPSEEK_API_KEY=sk-... python3 examples/first_agent_run.py --deepseek
```

实测：

```
status: success
final : 955
```

---

## 3. 三个缺陷

| # | 缺陷 | 现象 | 修法 |
|---|---|---|---|
| 1 | tool 消息 content 是 dict | OpenAI 兼容端点 400 | dict/list 序列化成 JSON 字符串 |
| 2 | `arguments` 可能是 JSON 字符串 | `constrain` 抛 AttributeError | 字符串就 json.loads |
| 3 | tool 消息缺 `tool_call_id`，且前面没有 assistant(tool_calls) | DeepSeek 422 | 补 id + 补 assistant 消息 |

为什么前两个测试抓不到：**MockLLMClient 不出 tool_calls**，测试永远走不到第二条消息。

第三个只有真模型（严格校验）才暴露：Ollama 不查，DeepSeek 查。

---

## 4. 验证

| 项 | 命令 | 结果 |
|---|---|---|
| 回归 | `pytest tests/test_tool_message_content_is_str.py` | 1 passed（含 id + assistant 顺序断言） |
| Mock | `python examples/first_agent_run.py` | success |
| DeepSeek | `--deepseek` | success，answer=955 = 真实数量 |
| 真实数量 | `find . -name '*.py' | wc -l` | 955 |

---

## 5. 未做

| 项 | 说明 |
|---|---|
| `:tools` 自动接线 | 产物只带配置，bash 实现要调用方注入（示例里手写 20 行） |
| 内置工具库 | 没有现成实现 |
| 流式输出 | 未验 |
