# US-29 交底：真实环境验收（P5-3）

> 基线：77ca4d8 · 日期：2026-10-14
> 故事：US-29（作为 O，我要真实环境验收，以便能用）
> 判据：真模型 + 真工具，端到端走通

---

## 1. 结论

**通过。** 真模型 Ollama qwen3:4b + 真工具（真起子进程）端到端走通。实测 1 passed（6.50s）。

---

## 2. 先修了一个阻塞缺陷

**真 provider 不传工具 schema** -> 模型永不出 tool_calls -> 真工具路径断。
MockLLMClient 自带 tool_calls，所以测试一直是绿的，**掩盖了这个洞**。

| 文件 | 改动 |
|---|---|
| runtime/llm_client.py | OpenAIClient / QwenProvider 的 achat 收 tools 并传给 API；AnthropicClient 转 Anthropic tools 并解析 tool_use |
| runtime/base_harness_v2.py | 每轮把 tool_registry.to_openai_schema() 传给 achat(tools=...) |
| tests/test_tool_schema_passed.py | 可捕获 provider：证明 harness 真传 tools，且 tool_calls 被执行 |

---

## 3. 验收读数

| 项 | 值 |
|---|---|
| 真模型 | Ollama qwen3:4b（http://127.0.0.1:11434/v1） |
| 真工具 | 真起子进程跑 shell（subprocess） |
| 断言 | 工具被调用；stdout 含 us29-ok |
| 结果 | 1 passed（6.50s） |

---

## 4. 复现

export PATH="$PWD/.racket/bin:$PATH"
AGENTLISP_REAL_ENV=1 AGENTLISP_REAL_MODEL=qwen3:4b pytest tests/test_us29_real_env.py -q --no-cov

默认 skip（CI 无 Ollama）。skip 写明了原因，不假绿。

---

## 5. 未做（诚实登记）

- 官方 API key（Anthropic / OpenAI）未验。本轮用 Ollama 作真模型。
- Anthropic 的 tool_use 解析只有单元级，未打真端点。
