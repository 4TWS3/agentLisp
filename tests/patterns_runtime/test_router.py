"""契约 CT-ROUTER-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2
import logging


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_router_behavior() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "router", "routes": ["deploy=>ops", "query=>kb"]}]
    from runtime.patterns import load

    load(h)
    rr = h.patterns.api("router")
    assert rr.route("deploy") == "ops"
    try:
        rr.route("nope")
        raise AssertionError("未覆盖意图应报错")
    except KeyError:
        logging.getLogger(__name__).debug("swallowed exception", exc_info=True)
    assert "pattern:router" in str(h.build_context()), "CT-ROUTER-01：上下文应含指令"


def test_router_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:router" not in str(h.build_context())
