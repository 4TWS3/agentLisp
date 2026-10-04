"""Pytest test suite for agentlisp_runtime."""

from __future__ import annotations

import pytest

from agentlisp_runtime.engine import AgentEngine
from agentlisp_runtime.models import (
    ActionType,
    Agent,
    AtomicAction,
    ExecutionContext,
    ExecutionStatus,
    Step,
    Tool,
    Workflow,
)


def test_agent_creation():
    tool = Tool(name="t1", description="d")
    wf = Workflow(name="wf1", steps=[], triggers=["manual"])
    agent = Agent(name="test-agent", purpose="p", tools=[tool], workflows=[wf])
    assert agent.name == "test-agent"
    assert agent.get_tool("t1") is not None
    assert agent.get_workflow("wf1") is not None


def test_step_creation():
    action = AtomicAction(name="a1", target="db", method="query", params=["SELECT 1"])
    step = Step(id="s1", action=action, next="s2", condition=True)
    assert step.id == "s1"
    assert step.action.type == ActionType.ATOMIC


def test_agent_name_validation():
    with pytest.raises(ValueError):
        Agent(name="  ", purpose="p")


@pytest.mark.asyncio
async def test_engine_run_simple_workflow():
    results_captured: dict[str, str] = {}

    class DummyTool:
        async def hello(self, name: str) -> dict:
            results_captured["hello"] = name
            return {"greeting": f"Hello, {name}!"}

    agent = Agent(
        name="demo",
        tools=[Tool(name="greet", description="greeter")],
        workflows=[
            Workflow(
                name="greet-flow",
                steps=[
                    Step(
                        id="say-hi",
                        action=AtomicAction(name="hi", target="greet", method="hello", params=["World"]),
                        next=None,
                    ),
                ],
            )
        ],
    )

    engine = AgentEngine(agent, tool_handlers={"greet": DummyTool()})
    ctx = ExecutionContext()
    result = await engine.run_workflow("greet-flow", ctx)

    assert result.success is True
    assert result.status == ExecutionStatus.SUCCESS
    assert results_captured.get("hello") == "World"
    assert ctx.get_result("say-hi") == {"greeting": "Hello, World!"}


@pytest.mark.asyncio
async def test_engine_missing_workflow():
    agent = Agent(name="a", tools=[], workflows=[])
    engine = AgentEngine(agent)
    result = await engine.run_workflow("not-found")
    assert result.success is False
    assert result.status == ExecutionStatus.FAILED


@pytest.mark.asyncio
async def test_engine_step_skipped():
    agent = Agent(
        name="a",
        workflows=[
            Workflow(
                name="wf",
                steps=[
                    Step(
                        id="s1",
                        action=AtomicAction(name="x", target="t", method="m", params=[]),
                        condition=False,
                        next=None,
                    ),
                ],
            )
        ],
    )
    engine = AgentEngine(agent)
    result = await engine.run_workflow("wf")
    assert result.success is True
    assert len(result.steps) == 1
    assert result.steps[0].status == ExecutionStatus.SKIPPED
