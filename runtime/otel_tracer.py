# -*- coding: utf-8 -*-
"""OpenTelemetry 集成 (SRS NFR-OBS-1)。

单文件模块、零业务副作用：若环境装了 observability 组，则真实建 span；
否则创建兼容的 Noop tracer，不影响 runtime/base_harness_v2 的零依赖路径。

对外 API：
  - create_tracer(service_name: str = "agentlisp") -> TracerProtocol
  - install_harness_tracer(harness: BaseHarnessV2, tracer_provider: Optional["TracerProvider"] = None)
    → 给 harness 注入 self.otel_tracer，并在每个 _react_step 调用时生成 span `agentlisp.react.turn`
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any, Dict, Iterator, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)

# Span 名对齐 SRS NFR-OBS-1：agentlisp.react.turn
AGENTLISP_TURN_SPAN = "agentlisp.react.turn"


class SpanProtocol(Protocol):
    def set_attribute(self, key: str, value: Any) -> None: ...
    def record_exception(self, exception: BaseException) -> None: ...
    def end(self) -> None: ...


class TracerProtocol(Protocol):
    @contextlib.contextmanager
    def start_as_current_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Iterator[SpanProtocol]: ...


class _NoopSpan:
    def set_attribute(self, key: str, value: Any) -> None:  # noqa: ARG002
        return None

    def record_exception(self, exception: BaseException) -> None:  # noqa: ARG002
        return None

    def end(self) -> None:
        return None


class _NoopTracer:
    """Noop 实现：无 opentelemetry 依赖时，保证 runtime 路径零开销通过。"""

    @contextlib.contextmanager
    def start_as_current_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Iterator[_NoopSpan]:  # noqa: ARG002
        yield _NoopSpan()


def _import_otel() -> Tuple[Optional[Any], Optional[Any], Optional[Any]]:
    """延迟 import：仅在真实需要 provider / exporter 时调用，失败返回 (None, None, None)。"""
    try:
        from opentelemetry import trace as _ot_trace  # type: ignore[import-not-found]
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-not-found]
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter  # type: ignore[import-not-found]
        return _ot_trace, TracerProvider, InMemorySpanExporter
    except Exception:  # noqa: BLE001
        return None, None, None


def create_tracer(
    service_name: str = "agentlisp",
    *,
    tracer_provider: Optional[Any] = None,
) -> TracerProtocol:
    """返回 TracerProtocol：优先用真实 OTel，否则 NoopTracer。"""
    ot_trace, TracerProviderCls, _ = _import_otel()
    if ot_trace is None or TracerProviderCls is None:
        return _NoopTracer()
    try:
        if tracer_provider is None:
            tracer_provider = TracerProviderCls()
            ot_trace.set_tracer_provider(tracer_provider)
        return tracer_provider.get_tracer(service_name)  # type: ignore[no-any-return]
    except Exception as exc:  # noqa: BLE001
        logger.warning("[otel] create_tracer fallback to noop: %s", exc)
        return _NoopTracer()


def install_harness_tracer(
    harness: Any,
    tracer_provider: Optional[Any] = None,
) -> TracerProtocol:
    """把 `harness.otel_tracer` 挂到 BaseHarnessV2。
    `_react_step` 内部若检测到有 otel_tracer，会自动包一层 `agentlisp.react.turn` span。"""
    tracer = create_tracer(getattr(harness, "agent_name", None) or "agentlisp", tracer_provider=tracer_provider)
    harness.otel_tracer = tracer
    return tracer


__all__ = [
    "AGENTLISP_TURN_SPAN",
    "TracerProtocol",
    "SpanProtocol",
    "create_tracer",
    "install_harness_tracer",
    "_NoopTracer",
]
