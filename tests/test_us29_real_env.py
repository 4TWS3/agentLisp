"""US-29：真实环境验收（真模型 + 真工具）。

只在 AGENTLISP_REAL_ENV=1 且 Ollama 可达时跑。
为什么默认 skip：CI 没有 Ollama。默认跑会假绿或假红。skip 要说明原因。

真模型：Ollama qwen3:4b（OpenAI 兼容端点）。
真工具：真的起子进程跑 shell。
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import subprocess
from typing import Any

import pytest

from runtime.base_harness_v2 import BaseHarnessV2
from runtime.llm_client import OpenAIClient

OLLAMA = "http://127.0.0.1:11434/v1"


_LOGGER = logging.getLogger(__name__)


def _reachable() -> bool:
    try:
        socket.create_connection(("127.0.0.1", 11434), timeout=1.0).close()
        return True
    except OSError as exc:
        # 不静默：说明为什么 skip
        _LOGGER.debug("Ollama 不可达（127.0.0.1:11434）：%s", exc)
        return False


pytestmark = pytest.mark.skipif(
    os.getenv("AGENTLISP_REAL_ENV") != "1" or not _reachable(),
    reason="真实环境验收需 AGENTLISP_REAL_ENV=1 且 Ollama 可达",
)


class _BashTool:
    """真工具：真的起子进程。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.stdout = ""
        self.stderr = ""
        self.exit_code = 0

    def names(self) -> list[str]:
        return ["bash"]

    def to_openai_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "Run a shell command and return its output.",
                    "parameters": {
                        "type": "object",
                        "properties": {"cmd": {"type": "string"}},
                        "required": ["cmd"],
                    },
                },
            }
        ]

    async def acall(self, name: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"name": name, "args": kwargs})
        cmd = str(kwargs.get("cmd") or kwargs.get("command") or "")
        cp = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        self.stdout, self.stderr, self.exit_code = cp.stdout, cp.stderr, cp.returncode
        return {"exit_code": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr}


def test_real_model_calls_real_tool() -> None:
    os.environ["OPENAI_BASE_URL"] = OLLAMA
    os.environ["OPENAI_API_KEY"] = "ollama"
    llm = OpenAIClient(model=os.getenv("AGENTLISP_REAL_MODEL", "qwen3:4b"), api_key="ollama")
    reg = _BashTool()
    h = BaseHarnessV2(
        {"system_prompt": "You are a ReAct agent. Use the bash tool when asked to run a command."},
        {},
        {},
        # bash 是副作用内置工具。不给护栏，constrain 会按 FR-CHECK-2 拦。
        # 这里给 approval 名单 + 非空 forbidden，属「已护栏」正例。
        {
            "constrain": {
                "require_human_approval": ["bash"],
                "forbidden_commands": ["rm -rf"],
            },
            "verify": {},
            "correct": {"max_retries": 1},
        },
        llm_client=llm,
        tool_registry=reg,
        max_turns=4,
    )
    asyncio.run(h.run("Use the bash tool to run exactly this command: echo us29-ok"))
    assert reg.calls, "真模型没有触发真工具"
    assert "us29-ok" in reg.stdout, "真工具没产生预期输出：" + repr(reg.stdout)
