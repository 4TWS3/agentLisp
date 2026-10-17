"""P0-2：Temporal 骨架必须显式降级，不许静默。

判据：
  - prefer_temporal=True 但 Temporal 只有骨架 → 退回 DirectRunner 且打 WARNING
  - DurableExecutionUnavailableError 与 FeatureNotInstalledError 不同类（语义不同）
"""

from __future__ import annotations

import logging

import pytest

from host.workflow import default_runner
from runtime.errors import DurableExecutionUnavailableError, FeatureNotInstalledError


def test_temporal_falls_back_loudly(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        runner = default_runner(prefer_temporal=True)
    assert type(runner).__name__ == "DirectRunner"
    msgs = [rec.message for rec in caplog.records]
    assert any("Temporal" in m for m in msgs), f"必须留痕，实际日志={msgs}"


def test_durable_error_is_distinct_from_missing_dep() -> None:
    assert not issubclass(DurableExecutionUnavailableError, FeatureNotInstalledError)
    assert issubclass(DurableExecutionUnavailableError, Exception)
