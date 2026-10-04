"""Pytest tests for runtime + host skeletons (v2 smoke)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "python"))


def test_runtime_imports() -> None:
    from runtime import (  # noqa: F401
        AgentLispError,
        BaseHarness,
        ExecutionTrace,
        FeatureNotInstalledError,
        HarnessError,
        ReActTurn,
        __version__,
    )
    assert __version__.startswith("2.")


@pytest.mark.asyncio
async def test_base_harness_mock_llm_completes() -> None:
    from runtime.base_harness import BaseHarness
    from runtime.llm_client import MockLLMClient

    llm = MockLLMClient(
        responses=[
            {"thought": "t1", "answer": "ALL-DONE"},
        ]
    )
    h = BaseHarness(agent_cfg={"name": "test", "purpose": "p"}, llm_client=llm)
    trace = await h.run_async({"x": 1})
    assert trace.status == "success"
    assert trace.agent_name == "test"
    assert "ALL-DONE" in trace.final_answer
    assert trace.turns
    assert trace.turns[0]["index"] == 0


def test_status_bar_composite() -> None:
    from runtime.status_bar import (
        CompositeStatusBar,
        LoggingStatusBar,
        PrintingStatusBar,
    )
    bar = CompositeStatusBar(PrintingStatusBar(), LoggingStatusBar())
    assert isinstance(bar.bars, tuple)
    assert len(bar.bars) == 2


def test_tool_registry_async() -> None:
    from runtime.mcp_client import ToolRegistry
    from runtime.errors import ToolNotFoundError

    reg = ToolRegistry()

    async def fn(x: int) -> int:
        return x * 2

    reg.register("double", fn)
    assert reg.has("double")
    assert asyncio.run(reg.call("double", x=21)) == 42
    with pytest.raises(ToolNotFoundError):
        reg.get("nope")


def test_memory_fs_layers() -> None:
    from runtime.memory_fs import L0_ATOMIC, L1_CONCEPT, L2_RULE, MemoryFS

    fs = MemoryFS()
    asyncio.run(fs.put(L0_ATOMIC, "a1.md", "# atomic 1"))
    asyncio.run(fs.put(L1_CONCEPT, "c1.md", "# concept 1"))
    asyncio.run(fs.put(L2_RULE, "r1.md", "# rule 1"))

    got = asyncio.run(fs.list_layer(L0_ATOMIC))
    assert got == ["a1.md"]
    assert asyncio.run(fs.get(L2_RULE, "r1.md")).startswith("# rule")


def test_feature_not_installed_message_mentions_install_command() -> None:
    from runtime.errors import FeatureNotInstalledError

    e = FeatureNotInstalledError("FastAPI", "web")
    assert "web" in str(e)
    assert "uv pip install" in str(e)


def test_host_imports_no_opt_deps() -> None:
    # 确保即使未安装 FastAPI / Temporal / docker，也能成功 import
    import host.gateway as g  # noqa: F401
    import host.workflow as w  # noqa: F401
    import host.sandbox as s  # noqa: F401
    assert issubclass(w.DirectRunner, w.WorkflowRunner)
    assert issubclass(s.NullSandbox, s.Sandbox)
    # Gateway 的 app 要么成功构建（环境装了 web optional 组），要么抛出 FeatureNotInstalledError/ImportError
    try:
        app = g.Gateway().app
    except (g.FeatureNotInstalledError, ImportError):
        return
    # 若能成功拿到 app，至少应该有 /health 路由
    routes = {getattr(r, "path", None) for r in getattr(app, "routes", [])}
    assert "/health" in routes or "/docs" in routes


def test_generated_agent_importable() -> None:
    import importlib
    importlib.invalidate_caches()
    mod = importlib.import_module("examples.dist.repair_agent")
    assert mod.AGENT_NAME == "document-repairer"
    assert "document-repairer" in mod.HARNESS_REGISTRY
    cls = mod.HARNESS_REGISTRY["document-repairer"]
    from runtime.base_harness import BaseHarness
    assert issubclass(cls, BaseHarness)


@pytest.mark.asyncio
async def test_direct_runner_roundtrip() -> None:
    from host.workflow import DirectRunner, WorkflowRequest
    from runtime.base_harness import BaseHarness

    h = BaseHarness(agent_cfg={"name": "r"})
    dr = DirectRunner()
    rid = await dr.submit(WorkflowRequest(agent_name="r", harness=h, inputs={"a": 1}))
    trace = await dr.wait(rid, timeout=10.0)
    assert trace.status == "success"
    assert rid in dr.traces
