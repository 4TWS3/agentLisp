"""Data models for Agent DSL runtime."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ActionType(str, Enum):  # noqa: UP042
    ATOMIC = "atomic"
    COMPOSITE = "composite"
    CUSTOM = "custom"


class ExecutionStatus(str, Enum):  # noqa: UP042
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class AtomicAction(BaseModel):
    name: str
    target: str
    method: str
    params: list[Any] = Field(default_factory=list)
    type: ActionType = ActionType.ATOMIC


class Tool(BaseModel):
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    handler: Callable[..., Awaitable[Any] | Any] | None = Field(default=None, exclude=True)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v


class Step(BaseModel):
    id: str
    action: AtomicAction | dict[str, Any]
    next: str | None = None
    condition: bool | str = True

    @field_validator("id")
    @classmethod
    def id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Step id cannot be empty")
        return v


class Workflow(BaseModel):
    name: str
    steps: list[Step] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)


class Agent(BaseModel):
    name: str
    purpose: str = ""
    tools: list[Tool] = Field(default_factory=list)
    workflows: list[Workflow] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Agent name cannot be empty")
        return v

    def get_tool(self, tool_name: str) -> Tool | None:
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    def get_workflow(self, workflow_name: str) -> Workflow | None:
        for wf in self.workflows:
            if wf.name == workflow_name:
                return wf
        return None


class ExecutionContext(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    variables: dict[str, Any] = Field(default_factory=dict)
    results: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def set_result(self, step_id: str, value: Any) -> None:
        self.results[step_id] = value

    def get_result(self, step_id: str, default: Any = None) -> Any:
        return self.results.get(step_id, default)


class StepExecutionResult(BaseModel):
    step_id: str
    status: ExecutionStatus
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class ExecutionResult(BaseModel):
    run_id: UUID
    agent_name: str
    workflow_name: str | None
    status: ExecutionStatus
    steps: list[StepExecutionResult] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS
