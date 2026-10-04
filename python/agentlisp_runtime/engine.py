"""Agent Engine - core execution engine that runs workflows defined via DSL."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

import structlog

from .models import (
    Agent,
    AtomicAction,
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    Step,
    StepExecutionResult,
    Workflow,
)

logger = structlog.get_logger()


class AgentEngine:
    def __init__(
        self,
        agent: Agent,
        tool_handlers: dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        self._agent = agent
        self._tool_handlers: dict[str, Callable[..., Any]] = tool_handlers or {}
        self._register_agent_tools()

    def _register_agent_tools(self) -> None:
        for tool in self._agent.tools:
            if tool.handler is not None and tool.name not in self._tool_handlers:
                self._tool_handlers[tool.name] = tool.handler

    def register_tool_handler(self, tool_name: str, handler: Callable[..., Any]) -> None:
        self._tool_handlers[tool_name] = handler

    async def run_workflow(
        self,
        workflow_name: str,
        context: ExecutionContext | None = None,
    ) -> ExecutionResult:
        start_time = time.perf_counter()
        context = context or ExecutionContext()

        workflow = self._agent.get_workflow(workflow_name)
        if workflow is None:
            return ExecutionResult(
                run_id=context.run_id,
                agent_name=self._agent.name,
                workflow_name=workflow_name,
                status=ExecutionStatus.FAILED,
                error=f"Workflow '{workflow_name}' not found",
            )

        logger.info(
            "workflow.start",
            agent=self._agent.name,
            workflow=workflow_name,
            run_id=str(context.run_id),
        )

        result = ExecutionResult(
            run_id=context.run_id,
            agent_name=self._agent.name,
            workflow_name=workflow_name,
            status=ExecutionStatus.RUNNING,
        )

        try:
            await self._execute_steps(workflow, context, result)
            result.status = ExecutionStatus.SUCCESS
        except Exception as exc:
            logger.exception("workflow.error", error=str(exc))
            result.status = ExecutionStatus.FAILED
            result.error = str(exc)

        result.total_duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "workflow.end",
            agent=self._agent.name,
            workflow=workflow_name,
            status=result.status.value,
            duration_ms=result.total_duration_ms,
        )
        return result

    async def _execute_steps(
        self,
        workflow: Workflow,
        context: ExecutionContext,
        result: ExecutionResult,
    ) -> None:
        step_map: dict[str, Step] = {s.id: s for s in workflow.steps}

        if not workflow.steps:
            return

        current_step_id: str | None = workflow.steps[0].id
        visited: set[str] = set()

        while current_step_id is not None:
            if current_step_id in visited:
                raise RuntimeError(f"Cycle detected in workflow at step: {current_step_id}")
            visited.add(current_step_id)

            step = step_map.get(current_step_id)
            if step is None:
                raise RuntimeError(f"Step not found: {current_step_id}")

            step_result = await self._execute_step(step, context)
            result.steps.append(step_result)

            if step_result.status == ExecutionStatus.FAILED:
                raise RuntimeError(f"Step '{step.id}' failed: {step_result.error}")

            if step.next is None or step.next is False:
                break

            current_step_id = step.next if isinstance(step.next, str) else None

    async def _execute_step(
        self,
        step: Step,
        context: ExecutionContext,
    ) -> StepExecutionResult:
        start_time = time.perf_counter()

        if not self._evaluate_condition(step.condition, context):
            return StepExecutionResult(
                step_id=step.id,
                status=ExecutionStatus.SKIPPED,
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )

        logger.debug("step.start", step=step.id)

        try:
            action = step.action
            if isinstance(action, AtomicAction):
                output = await self._execute_atomic_action(action, context)
            elif isinstance(action, dict):
                atomic = AtomicAction(**action)
                output = await self._execute_atomic_action(atomic, context)
            else:
                output = None

            context.set_result(step.id, output)

            return StepExecutionResult(
                step_id=step.id,
                status=ExecutionStatus.SUCCESS,
                output=output,
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )
        except Exception as exc:
            logger.exception("step.error", step=step.id, error=str(exc))
            return StepExecutionResult(
                step_id=step.id,
                status=ExecutionStatus.FAILED,
                error=str(exc),
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )

    def _evaluate_condition(
        self,
        condition: bool | str,
        context: ExecutionContext,
    ) -> bool:
        if isinstance(condition, bool):
            return condition
        if isinstance(condition, str):
            try:
                return bool(eval(condition, {"context": context}))
            except Exception:
                logger.warning("condition.eval_failed", condition=condition)
                return False
        return True

    async def _execute_atomic_action(
        self,
        action: AtomicAction,
        context: ExecutionContext,
    ) -> Any:
        handler = self._tool_handlers.get(action.target)
        if handler is None:
            logger.warning(
                "handler.not_found",
                target=action.target,
                method=action.method,
            )
            return {
                "_status": "no_handler",
                "target": action.target,
                "method": action.method,
                "params": action.params,
            }

        resolved_params = self._resolve_params(action.params, context)
        method_fn = getattr(handler, action.method, None) if not callable(handler) else handler

        if method_fn is not None and callable(method_fn):
            if asyncio.iscoroutinefunction(method_fn):
                return await method_fn(*resolved_params)
            return method_fn(*resolved_params)

        if callable(handler):
            if asyncio.iscoroutinefunction(handler):
                return await handler(action.method, *resolved_params)
            return handler(action.method, *resolved_params)

        raise RuntimeError(
            f"No callable handler for target='{action.target}', method='{action.method}'"
        )

    def _resolve_params(self, params: list[Any], context: ExecutionContext) -> list[Any]:
        resolved: list[Any] = []
        for p in params:
            if isinstance(p, str) and p.startswith("$."):
                var_path = p[2:]
                value = self._resolve_path(var_path, context)
                resolved.append(value)
            else:
                resolved.append(p)
        return resolved

    @staticmethod
    def _resolve_path(path: str, context: ExecutionContext) -> Any:
        parts = path.split(".")
        if not parts:
            return None
        root = parts[0]
        rest = parts[1:]
        data: Any = None
        if root == "results":
            data = context.results
        elif root == "vars" or root == "variables":
            data = context.variables
        elif root == "meta" or root == "metadata":
            data = context.metadata
        else:
            return None
        for part in rest:
            data = data.get(part) if isinstance(data, dict) else getattr(data, part, None)
            if data is None:
                break
        return data
