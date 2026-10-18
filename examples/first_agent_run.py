"""跑 examples/first-agent.al 的编译产物。

为什么需要这个文件：编译产物只带配置，**工具实现要由调用方注入**
（BaseHarnessV2 不会自己从 :tools 造出 bash）。这是当前的接线方式。

用法：
  python examples/first_agent_run.py            # Mock 模型，只看链路通不通
  python examples/first_agent_run.py --real     # 真模型（需 Ollama 在 11434）
  python examples/first_agent_run.py --deepseek # DeepSeek（需 ~/.deepseek-key）
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE / "dist"))

from first_agent import FirstAgentHarness  # noqa: E402


class BashTool:
    """最小工具注册表：实现 ToolRegistryProtocol 的三个方法（names / schema / acall）。"""

    def names(self) -> list[str]:
        return ["bash"]

    def to_openai_schema(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "Run a shell command and return stdout/stderr.",
                    "parameters": {
                        "type": "object",
                        "properties": {"cmd": {"type": "string"}},
                        "required": ["cmd"],
                    },
                },
            }
        ]

    async def acall(self, name: str, **kwargs: object) -> dict[str, object]:
        cmd = str(kwargs.get("cmd") or kwargs.get("command") or "")
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return {"exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def _deepseek_key() -> str:
    """从环境或 ~/.deepseek-key 读 key（文件优先，方便本机开发）。"""
    import os
    import pathlib

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

        llm = OpenAIClient(
            # 默认用 flash：便宜。要更强换 DEEPSEEK_MODEL=deepseek-v4-pro。
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            api_key=_deepseek_key(),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        )
        h = FirstAgentHarness(llm_client=llm, tool_registry=BashTool())
    elif "--real" in args:
        from runtime.llm_client import OpenAIClient

        llm = OpenAIClient(
            model="qwen3:4b",
            api_key="ollama",
            base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1"),
        )
        h = FirstAgentHarness(llm_client=llm, tool_registry=BashTool())
    else:
        h = FirstAgentHarness(tool_registry=BashTool())

    trace = asyncio.run(h.run("仓库里一共有多少个 .py 文件（含子目录）？只回答数字。"))
    print("status:", trace.status)
    print("final :", trace.final_answer)


if __name__ == "__main__":
    main()
