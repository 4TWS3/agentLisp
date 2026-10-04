"""LLM Client protocol + Provider enum + CircuitBreaker + Mock implementation.

CR-16 P1-5 新增：
  * PROVIDER_ENUM: anthropic / openai / qwen / mock（对齐 SRS FR-PARSER-2）
  * LLMProviderProtocol: achat(messages, **) → dict（runtime 通用，兼容 BaseHarnessV2.achat 签名）
  * CircuitBreaker: 连续 N 次 4xx/5xx/异常 失败 → open → on_failure=fallback-model → abort
  * LLMProviderOrchestrator: primary / fallback_provider 双 provider 过 CircuitBreaker；
    Constrain 层 forbid_context_keys 预过滤 messages 防止 context leakage（FR-CHECK-3 runtime 层）
"""

from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from .base_harness import ExecutionTrace
from .errors import FeatureNotInstalledError, HarnessError

# SRS §3 FR-PARSER-2: Provider enum（字符串形式，编译期与 runtime 双端一致）
PROVIDER_ENUM: set[str] = {"anthropic", "openai", "qwen", "mock"}
ProviderName = Literal["anthropic", "openai", "qwen", "mock"]

# SRS §4 ERR_CONTEXT_LEAKAGE（runtime 层：在消息真正发往 provider 前再拦一次）
ERR_CONTEXT_LEAKAGE = "ERR_CONTEXT_LEAKAGE"


class LLMClient(Protocol):
    async def next(
        self,
        prompt: dict[str, Any],
        history: list[dict[str, Any]],
        trace: ExecutionTrace,
    ) -> dict[str, Any]: ...


class LLMProviderProtocol(Protocol):
    """统一 Provider 协议。所有真实 provider（anthropic/openai/qwen/mock）都实现这个接口。"""

    name: ProviderName

    async def achat(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]: ...


# ==============================================================================
# Mock Provider（零网络依赖，CI 基线）
# ==============================================================================


class MockLLMClient:
    """遗留版本（next()），兼容 base_harness 老签名。"""

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
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


class MockProvider:
    """新版 provider（achat 签名），零网络依赖，pytest / CI 默认 provider。"""

    name: ProviderName = "mock"

    def __init__(
        self,
        responses: list[dict[str, Any]] | None = None,
        *,
        fail_n_times: int = 0,
        failure_code: int = 500,
    ) -> None:
        self.responses: deque[dict[str, Any]] = deque(responses or [])
        self.fail_n_times = int(fail_n_times)
        self.failure_code = int(failure_code)
        self._failure_counter = 0
        self.calls: list[dict[str, Any]] = []

    async def achat(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"messages": list(messages), "kwargs": dict(kwargs)})
        if self._failure_counter < self.fail_n_times:
            self._failure_counter += 1
            msg = (
                f"MockProvider synthetic {self.failure_code} failure "
                f"({self._failure_counter}/{self.fail_n_times})"
            )
            raise ProviderHTTPError(
                status_code=self.failure_code,
                message=msg,
                provider_name=self.name,
            )
        if self.responses:
            return dict(self.responses.popleft())
        return {
            "role": "assistant",
            "content": (
                f"[MockProvider end-of-queue @{len(self.calls)} calls] "
                "Treat this as FINAL_ANSWER if no tool_calls emitted."
            ),
            "tool_calls": None,
        }


# ==============================================================================
# Provider 层错误（给 CircuitBreaker 判断 4xx/5xx）
# ==============================================================================


class ProviderHTTPError(HarnessError):
    """真实 Provider 4xx/5xx（或模拟）。status_code / provider_name 字段可拿，便于 CircuitBreaker 统计。"""

    def __init__(
        self,
        status_code: int,
        message: str,
        provider_name: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = int(status_code)
        self.provider_name = provider_name
        self.message = message

    @property
    def is_client_error(self) -> bool:  # 4xx
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:  # 5xx
        return 500 <= self.status_code < 600


# ==============================================================================
# Circuit Breaker（FR-CORRECT-2：连续 N 次失败 → open → fallback → abort）
# ==============================================================================


@dataclass
class CircuitBreaker:
    """连续失败计数断路器。状态机 closed → open → half-open → closed/open。

    failure_threshold=N：N 次 Provider 4xx/5xx/异常 → open；
    cooloff_seconds=T：open 后冷却 T 秒 → 允许 half-open 打 1 次试探；
    half_open_success_threshold=1：half-open 成功 1 次 → closed；连续再 1 次失败 → 再次 open。
    """

    failure_threshold: int = 3
    cooloff_seconds: float = 30.0
    half_open_success_threshold: int = 1
    state: str = "closed"  # closed / open / half-open
    failure_count: int = 0
    half_open_successes: int = 0
    opened_at_monotonic: float = 0.0
    history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.failure_threshold <= 0:
            raise ValueError("CircuitBreaker.failure_threshold must be >= 1")
        if self.cooloff_seconds < 0:
            raise ValueError("CircuitBreaker.cooloff_seconds must be >= 0")
        if self.half_open_success_threshold <= 0:
            raise ValueError("CircuitBreaker.half_open_success_threshold must be >= 1")

    @property
    def can_allow_request(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            now = time.monotonic()
            if now - self.opened_at_monotonic >= self.cooloff_seconds:
                self.state = "half-open"
                self.half_open_successes = 0
                return True
            return False
        # half-open：严格只允许 half_open_success_threshold 次试探，其余全拒
        return self.half_open_successes < self.half_open_success_threshold

    def record_success(self, provider_name: str = "") -> None:
        self.history.append(
            {"event": "success", "provider": provider_name, "ts_monotonic": time.monotonic()}
        )
        if self.state == "half-open":
            self.half_open_successes += 1
            if self.half_open_successes >= self.half_open_success_threshold:
                self.state = "closed"
                self.failure_count = 0
                self.half_open_successes = 0
        elif self.state == "closed":
            # closed 下遇到 1 次成功就清零连续失败计数（recover_after_success）
            self.failure_count = 0

    def record_failure(self, reason: str, provider_name: str = "") -> None:
        self.history.append(
            {
                "event": "failure",
                "provider": provider_name,
                "reason": reason,
                "ts_monotonic": time.monotonic(),
            }
        )
        self.failure_count += 1
        if self.state == "half-open":
            self.state = "open"
            self.opened_at_monotonic = time.monotonic()
            self.half_open_successes = 0
            return
        if self.state == "closed" and self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.opened_at_monotonic = time.monotonic()

    def stats(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "half_open_successes": self.half_open_successes,
            "failure_threshold": self.failure_threshold,
            "cooloff_seconds": self.cooloff_seconds,
            "events_total": len(self.history),
        }


# ==============================================================================
# ERR_CONTEXT_LEAKAGE runtime 层过滤（Constrain.forbidden_context_keys）
# ==============================================================================


def validate_provider_name(name: str) -> ProviderName:
    """FR-PARSER-2 运行时二次校验：name ∉ PROVIDER_ENUM → ValueError。

    大小写敏感（对齐 compiler 侧 parse-model L125-L145，FR-PARSER-2 原字符串枚举）。
    """
    n = str(name)
    if n not in PROVIDER_ENUM:
        raise ValueError(f"FR-PARSER-2: provider={name!r} 不在枚举 {sorted(PROVIDER_ENUM)}")
    return n  # type: ignore[return-value]


def filter_forbidden_context_keys(
    messages: list[dict[str, Any]],
    forbidden_context_keys: list[str] | None,
) -> tuple[bool, str]:
    """在消息真正发送前扫描 messages 中是否含有 Constrain.forbidden_context_keys。

    返回 (passed, err_or_ok)。命中：passed=False, err 以 ERR_CONTEXT_LEAKAGE 开头。
    """
    if not forbidden_context_keys:
        return True, "OK"
    text_blobs: list[str] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        c = m.get("content")
        if isinstance(c, str):
            text_blobs.append(c)
            continue
        if isinstance(c, list):
            for block in c:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    text_blobs.append(block["text"])
    for forbidden in forbidden_context_keys:
        if not forbidden:
            continue
        needle = str(forbidden)
        for idx, blob in enumerate(text_blobs):
            if needle in blob:
                truncated = blob[:200].replace("\n", "\\n")
                return False, (
                    f"{ERR_CONTEXT_LEAKAGE}: "
                    f"runtime Constrain.forbidden_context_keys 命中 key={needle!r} "
                    f"在 messages[{idx}] content: {truncated!r}"
                )
    return True, "OK"


# ==============================================================================
# Provider Orchestrator（primary + 过 CircuitBreaker + fallback + abort 策略）
# ==============================================================================


class LLMProviderOrchestrator:
    """主 provider + 可选 fallback_provider；每一次调用经过 CircuitBreaker + 上下文过滤。

    策略：
      - primary 过 circuit_breaker。如果 breaker.open：
         * on_failure == "fallback_model"（或 "fallback-model"）→ 用 fallback_provider 再试；
         * on_failure == "abort" → 直接抛 CircuitBroken（上层 catch → trace.status=failed）；
         * on_failure == "ask_human"（或 "ask-human"）→ 抛 CircuitBroken 给上层挂起。
    """

    def __init__(
        self,
        primary: LLMProviderProtocol,
        *,
        fallback_provider: LLMProviderProtocol | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        on_failure: str = "ask-human",
        forbidden_context_keys: list[str] | None = None,
    ) -> None:
        # FR-PARSER-2 连字符下划线都兼容（runtime 层）
        norm_on_fail = str(on_failure).strip().lower().replace("_", "-")
        if norm_on_fail not in {"ask-human", "fallback-model", "abort"}:
            raise ValueError(
                f"FR-PARSER-5: orchestrator.on_failure={on_failure!r} 不在枚举 "
                "{ask-human, fallback-model, abort}"
            )
        self.primary = primary
        self.fallback_provider = fallback_provider
        self.circuit_breaker: CircuitBreaker = circuit_breaker or CircuitBreaker()
        self.on_failure = norm_on_fail
        self.forbidden_context_keys = list(forbidden_context_keys or [])
        self._last_error: str | None = None
        self._used_fallback: bool = False
        validate_provider_name(primary.name)
        if fallback_provider is not None:
            validate_provider_name(fallback_provider.name)

    # ------------------------------------------------------------------ core
    async def achat(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        ok, reason = filter_forbidden_context_keys(messages, self.forbidden_context_keys)
        if not ok:
            # FR-CHECK-3 runtime：命中 forbidden_context_keys → 直接 HarnessError，
            # 上层 run() catch → trace.status=blocked
            raise HarnessError(reason)

        # (1) Primary
        primary_tried = False
        if self.circuit_breaker.can_allow_request:
            primary_tried = True
            try:
                result = await self.primary.achat(messages, **kwargs)
            except (ProviderHTTPError, TimeoutError) as exc:
                status_code = getattr(exc, "status_code", 500)
                self.circuit_breaker.record_failure(
                    reason=f"{type(exc).__name__}(status={status_code}) {exc}",
                    provider_name=self.primary.name,
                )
                self._last_error = f"[primary-{self.primary.name}] {exc}"
            except Exception as exc:
                status_code = getattr(exc, "status_code", 500)
                self.circuit_breaker.record_failure(
                    reason=f"{type(exc).__name__}(status={status_code}) {exc}",
                    provider_name=self.primary.name,
                )
                self._last_error = f"[primary-{self.primary.name}] {exc}"
            else:
                self.circuit_breaker.record_success(provider_name=self.primary.name)
                return result
        else:
            self._last_error = (
                f"CircuitBreaker state={self.circuit_breaker.state} "
                f"failure_count={self.circuit_breaker.failure_count} → skip primary"
            )
        _ = primary_tried

        # (2) Fallback-model（fallback_provider 不受同一 breaker 计数，
        #     避免 provider 都挂时无限叠加）—— 仅在 primary 明确失败（breaker open / exception）时走 fallback
        if self.on_failure == "fallback-model" and self.fallback_provider is not None:
            self._used_fallback = True
            try:
                return await self.fallback_provider.achat(messages, **kwargs)
            except Exception as exc:  # pragma: no cover - synthetic
                self._last_error = f"[fallback-{self.fallback_provider.name}] {exc}"

        # (3) Abort / Ask-human：都以 CircuitBroken 暴露，上层按 on_failure 路由
        raise CircuitBroken(
            strategy=self.on_failure,
            breaker_stats=self.circuit_breaker.stats(),
            last_error=self._last_error,
            used_fallback=self._used_fallback,
        )


class CircuitBroken(HarnessError):
    """FR-CORRECT-2：circuit breaker 触达 failure_threshold → 抛给上层 → trace.status=failed / 挂起 HITL。"""

    def __init__(
        self,
        strategy: str,
        breaker_stats: dict[str, Any],
        last_error: str | None,
        used_fallback: bool,
    ) -> None:
        summary = (
            f"circuit_break: strategy={strategy}; "
            f"breaker_state={breaker_stats.get('state')} "
            f"failures={breaker_stats.get('failure_count')}/"
            f"{breaker_stats.get('failure_threshold')}; "
            f"used_fallback={used_fallback}; "
            f"last_error={last_error or '(none)'}"
        )
        super().__init__(summary)
        self.strategy = strategy
        self.breaker_stats = dict(breaker_stats)
        self.last_error = last_error
        self.used_fallback = bool(used_fallback)


# ==============================================================================
# 外部真实 Provider（网络依赖，FeatureNotInstalledError 时抛）——骨架层
# ==============================================================================


class OpenAIClient:
    """Thin OpenAI client. Requires `uv pip install 'agentlisp[llm]'`."""

    name: ProviderName = "openai"

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None) -> None:
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
            {
                "role": "system",
                "content": "You are a ReAct agent. Output JSON with keys thought/action/action_input or answer.",
            },
            {"role": "user", "content": str(prompt)},
        ]
        for h in history:
            role = "assistant" if h.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": str(h)})
        resp = await self.client.chat.completions.create(model=self.model, messages=messages)
        content = resp.choices[0].message.content or "{}"
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"thought": content[:1000], "answer": content}

    async def achat(  # type: ignore[override]
        self, messages: list[dict[str, Any]], **_kwargs: Any
    ) -> dict[str, Any]:
        try:
            from openai import APIStatusError  # type: ignore[import-not-found]
        except Exception:  # pragma: no cover
            APIStatusError = Exception  # type: ignore[misc,assignment]
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
        except APIStatusError as exc:
            status = int(getattr(exc, "status_code", 500))
            raise ProviderHTTPError(
                status_code=status,
                message=f"OpenAI HTTP {status}: {exc}",
                provider_name=self.name,
            ) from exc
        choice = resp.choices[0].message
        tool_calls = None
        raw_tc = getattr(choice, "tool_calls", None)
        if raw_tc:
            tool_calls = [
                {
                    "id": getattr(t, "id", f"tc_{i}"),
                    "type": "function",
                    "function": {
                        "name": getattr(t.function, "name", ""),
                        "arguments": json.loads(getattr(t.function, "arguments", "{}") or "{}"),
                    },
                }
                for i, t in enumerate(raw_tc)
            ]
        return {
            "role": "assistant",
            "content": getattr(choice, "content", None),
            "tool_calls": tool_calls,
        }


class AnthropicClient:
    name: ProviderName = "anthropic"

    def __init__(
        self, model: str = "claude-3-5-sonnet-20240620", api_key: str | None = None
    ) -> None:
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
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"thought": content[:1000], "answer": content}

    async def achat(  # type: ignore[override]
        self, messages: list[dict[str, Any]], **_kwargs: Any
    ) -> dict[str, Any]:
        # Anthropic SDK：messages 至少要 1 条 user；把 system role 拆到 system 参数
        system_parts: list[str] = []
        cleaned: list[dict[str, Any]] = []
        for m in messages:
            role = str(m.get("role", "user"))
            c = m.get("content")
            text = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
            if role == "system":
                system_parts.append(text)
                continue
            if role in {"user", "assistant"}:
                cleaned.append({"role": role, "content": text})
        create_kwargs: dict[str, Any] = {"model": self.model, "max_tokens": 8192}
        if system_parts:
            create_kwargs["system"] = "\n\n".join(system_parts)
        if not cleaned:
            cleaned = [{"role": "user", "content": "(no user message)"}]
        create_kwargs["messages"] = cleaned
        msg = await self.client.messages.create(**create_kwargs)
        content = "".join(
            block.text for block in msg.content if getattr(block, "type", None) == "text"
        )
        return {"role": "assistant", "content": content, "tool_calls": None}


class QwenProvider:
    """Qwen / DashScope open-source compatible 层（openai 兼容 base_url）。

    Provider enum（qwen）= FR-PARSER-2；真实 API Key 走 DASHSCOPE_API_KEY 或 QWEN_API_KEY。
    """

    name: ProviderName = "qwen"

    def __init__(self, model: str = "qwen2.5-72b-instruct", api_key: str | None = None) -> None:
        try:
            from openai import AsyncOpenAI  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise FeatureNotInstalledError("Qwen (DashScope OpenAI-compat)", "llm") from exc
        key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        if not key:
            raise FeatureNotInstalledError(
                "Qwen", "llm", details="Missing DASHSCOPE_API_KEY / QWEN_API_KEY env var"
            )
        self.model = model
        self.client = AsyncOpenAI(
            api_key=key,
            base_url=os.getenv(
                "QWEN_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        )

    async def achat(  # type: ignore[override]
        self, messages: list[dict[str, Any]], **_kwargs: Any
    ) -> dict[str, Any]:
        try:
            from openai import APIStatusError  # type: ignore[import-not-found]
        except Exception:  # pragma: no cover
            APIStatusError = Exception  # type: ignore[misc,assignment]
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
        except APIStatusError as exc:
            status = int(getattr(exc, "status_code", 500))
            raise ProviderHTTPError(
                status_code=status,
                message=f"Qwen HTTP {status}: {exc}",
                provider_name=self.name,
            ) from exc
        choice = resp.choices[0].message
        raw_tc = getattr(choice, "tool_calls", None)
        tool_calls = None
        if raw_tc:
            tool_calls = [
                {
                    "id": getattr(t, "id", f"tc_{i}"),
                    "type": "function",
                    "function": {
                        "name": getattr(t.function, "name", ""),
                        "arguments": json.loads(getattr(t.function, "arguments", "{}") or "{}"),
                    },
                }
                for i, t in enumerate(raw_tc)
            ]
        return {
            "role": "assistant",
            "content": getattr(choice, "content", None),
            "tool_calls": tool_calls,
        }


__all__ = [
    "ERR_CONTEXT_LEAKAGE",
    "PROVIDER_ENUM",
    "AnthropicClient",
    "CircuitBreaker",
    "CircuitBroken",
    "CircuitBrokenError",
    "HarnessError",
    "LLMClient",
    "LLMProviderOrchestrator",
    "LLMProviderProtocol",
    "MockLLMClient",
    "MockProvider",
    "OpenAIClient",
    "ProviderHTTPError",
    "ProviderName",
    "QwenProvider",
    "filter_forbidden_context_keys",
    "validate_provider_name",
]

# ruff: noqa: N818 - backward compat: CircuitBroken is a HarnessError, name intentionally matches FR-CORRECT-2
# "circuit_break: strategy=..." trace.error 前缀；同时暴露 CircuitBrokenError 别名给 N818 校验用户。
CircuitBrokenError = CircuitBroken  # type: ignore[valid-type]
