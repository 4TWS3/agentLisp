"""LLM Client protocol + Mock implementation (no network required)."""

from __future__ import annotations

import os
from typing import Any, Optional, Protocol

from .base_harness import ExecutionTrace
from .errors import FeatureNotInstalledError


class LLMClient(Protocol):
    async def next(
        self,
        prompt: dict[str, Any],
        history: list[dict[str, Any]],
        trace: ExecutionTrace,
    ) -> dict[str, Any]: ...


class MockLLMClient:
    def __init__(self, responses: Optional[list[dict[str, Any]]] = None) -> None:
        self.responses = list(responses or [])
        self.cursor = 0

    async def next(
        self,
        prompt: dict[str, Any],
        history: list[dict[str, Any]],
        trace: ExecutionTrace,
    ) -> dict[str, Any]:
        if self.cursor < len(self.responses):
            r = self.responses[self.cursor]
            self.cursor += 1
            return r
        return {
            "thought": f"MockLLM: end of preset responses @turn {len(trace.turns)}",
            "answer": f"mock-done (inputs={prompt.get('inputs')})",
        }


class OpenAIClient:
    """Thin OpenAI client. Requires `uv pip install 'agentlisp[llm]'`."""

    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None) -> None:
        try:
            from openai import AsyncOpenAI  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise FeatureNotInstalledError("OpenAI", "llm") from exc
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    async def next(
        self,
        prompt: dict[str, Any],
        history: list[dict[str, Any]],
        trace: ExecutionTrace,
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": "You are a ReAct agent. Output JSON with keys thought/action/action_input or answer."},
            {"role": "user", "content": str(prompt)},
        ]
        for h in history:
            role = "assistant" if h.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": str(h)})
        resp = await self.client.chat.completions.create(model=self.model, messages=messages)
        content = resp.choices[0].message.content or "{}"
        import json
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"thought": content[:1000], "answer": content}


class AnthropicClient:
    def __init__(self, model: str = "claude-3-5-sonnet-20240620", api_key: Optional[str] = None) -> None:
        try:
            from anthropic import AsyncAnthropic  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise FeatureNotInstalledError("Anthropic", "llm") from exc
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    async def next(
        self,
        prompt: dict[str, Any],
        history: list[dict[str, Any]],
        trace: ExecutionTrace,
    ) -> dict[str, Any]:
        messages = [{"role": "user", "content": str(prompt)}]
        msg = await self.client.messages.create(
            model=self.model, max_tokens=2048, messages=messages
        )
        content = "".join(
            block.text for block in msg.content if getattr(block, "type", None) == "text"
        )
        import json
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"thought": content[:1000], "answer": content}
