# 内置工具开箱可用（runtime/builtin_tools.py）

> 日期：2026-10-18
> 判据：`(:tools (import-builtin bash))` 不改调用方代码就能用

---

## 1. 结论

DSL 声明什么工具，运行时就有什么工具。示例代码从 60 行降到 45 行，且**不再手写工具**。

---

## 2. 做了什么

| 项 | 内容 |
|---|---|
| 新模块 | `runtime/builtin_tools.py`：`BuiltinToolRegistry`（满足 ToolRegistryProtocol） |
| 支持工具 | `bash` / `read-file` / `write-back` / `patch-text` / `grep` |
| 自动接线 | `BaseHarnessV2.__init__`：没注入 registry 时按 `tools_config.import_builtins` 自动建 |
| 失败方式 | 声明了没实现的工具 → **构造时抛错**并列出支持清单（不静默跳过） |

---

## 3. 验证（实测）

| 项 | 结果 |
|---|---|
| 示例（Mock，不注入 registry） | `tools: ['bash']`，status success |
| 示例（DeepSeek flash） | `final: 956`（= 仓库 .py 真实数量） |
| 单元测试 | `tests/test_builtin_tools.py` 9 passed |

---

## 4. 安全边界（必须知道）

- `bash` 用 `shell=True`，模型给什么命令就跑什么。
- **真正的闸在 `constrain`**（`require_human_approval` / `forbidden_commands`），不在本模块。
- 未做：命令白名单、超时外的资源限制、沙箱。要上生产得配 `host/sandbox.py`。

---

## 5. 未做

| 项 | 说明 |
|---|---|
| 副作用内置工具 | `git-push` / `wget` / `curl` / `scp` / `dd` / `chmod` / `sudo` 未实现（真要用请先定参数 schema） |
| MCP 工具 | `mcp_servers` 仍未接线 |
| `define_tools` | DSL 里自定义工具的数据块未消费 |
