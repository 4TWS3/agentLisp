"""跑 examples/first-agent.al 的编译产物。

工具开箱可用：产物里带 `tools_config.import_builtins`，
BaseHarnessV2 会自动建内置工具注册表（runtime/builtin_tools.py），不用手写。

用法：
  python examples/first_agent_run.py             # Mock 模型，只看链路通不通
  python examples/first_agent_run.py --real      # Ollama（需 11434 在跑）
  python examples/first_agent_run.py --deepseek  # DeepSeek（需 DEEPSEEK_API_KEY 或 ~/.deepseek-key）
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE / "dist"))

from first_agent import FirstAgentHarness  # noqa: E402


def _deepseek_key() -> str:
    """从环境或 ~/.deepseek-key 读 key（文件优先，方便本机开发）。"""
    k = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if k:
        return k
    p = pathlib.Path.home() / ".deepseek-key"
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    raise SystemExit("缺 DeepSeek key：设 DEEPSEEK_API_KEY，或写入 ~/.deepseek-key")


def main() -> None:
    args = set(sys.argv[1:])
    if "--deepseek" in args:
        from runtime.llm_client import OpenAIClient

        h = FirstAgentHarness(
            llm_client=OpenAIClient(
                # 默认用 flash：便宜。要更强换 DEEPSEEK_MODEL=deepseek-v4-pro。
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
                api_key=_deepseek_key(),
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            )
        )
    elif "--real" in args:
        from runtime.llm_client import OpenAIClient

        h = FirstAgentHarness(
            llm_client=OpenAIClient(
                model="qwen3:4b",
                api_key="ollama",
                base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"),
            )
        )
    else:
        h = FirstAgentHarness()

    trace = asyncio.run(h.run("仓库里一共有多少个 .py 文件（含子目录）？只回答数字。"))
    print("tools:", h.tool_registry.names() if h.tool_registry else [])
    print("status:", trace.status)
    print("final :", trace.final_answer)


if __name__ == "__main__":
    main()
