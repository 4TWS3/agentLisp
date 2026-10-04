"""Workflow runner: DirectRunner (always available) + TemporalRunner (optional dep).

额外提供 HITL 人在回路的内存版 InMemoryHITLRunner（NFR-SEC-1b）：
  - 若约束里 require_approval 的工具被调用 → status=human_required 且停在 require_approval_queue；
  - 调用 approve(run_id, tool_name) / reject(run_id, tool_name) 后 workflow 继续（或失败）。
"""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

from runtime.errors import FeatureNotInstalledError
from runtime.base_harness import BaseHarness, ExecutionTrace


@dataclass
class WorkflowRequest:
    agent_name: str
    harness: BaseHarness
    inputs: dict[str, Any]
    workflow: Optional[str] = None
    run_id: Optional[str] = None


@dataclass
class HITLSuspension:
    run_id: str
    tool_name: str
    args: Dict[str, Any]
    approvable_event: asyncio.Event = field(default_factory=asyncio.Event)
    decision: Optional[str] = None  # "approve" | "reject"

    def resolve(self, decision: str) -> None:
        self.decision = decision
        self.approvable_event.set()


class WorkflowRunner(ABC):
    @abstractmethod
    async def submit(self, req: WorkflowRequest) -> str: ...
    @abstractmethod
    async def wait(self, run_id: str, timeout: float = 300.0) -> ExecutionTrace: ...


class DirectRunner(WorkflowRunner):
    """In-process async runner. Always available — zero external dependencies."""

    def __init__(self) -> None:
        self.traces: dict[str, ExecutionTrace] = {}
        self._tasks: dict[str, asyncio.Task[ExecutionTrace]] = {}

    async def submit(self, req: WorkflowRequest) -> str:
        run_id = req.run_id or os.urandom(8).hex()

        async def _task() -> ExecutionTrace:
            trace = await req.harness.run_async(inputs=req.inputs, workflow=req.workflow)
            self.traces[run_id] = trace
            return trace

        self._tasks[run_id] = asyncio.create_task(_task())
        return run_id

    async def wait(self, run_id: str, timeout: float = 300.0) -> ExecutionTrace:
        if run_id in self.traces:
            return self.traces[run_id]
        task = self._tasks.get(run_id)
        if task is None:
            raise KeyError(f"no run_id: {run_id}")
        trace = await asyncio.wait_for(task, timeout=timeout)
        return trace


class InMemoryHITLRunner(WorkflowRunner):
    """SRS NFR-SEC-1b：内存版 HITL Runner，不依赖 temporalio，可本地 pytest。

    工作流：
      1. submit(req) 启动一个长运行 task；
      2. task 里按 Harness 的顺序每步跑 step(1)，
         在每次 Constrain → Execute → Verify → Correct 前，若 tool_name 在 harness_config/correct/require_approval 里
         或 constrain_config 的 require_approval 里 → 入队 suspend_queue → status_bar/human_required → 等待 approve()；
      3. approve() → 放行 execute；reject() → 立即 failed，trace.status="failed" 且 error="human_rejected"。
    """

    def __init__(self) -> None:
        self.traces: Dict[str, Any] = {}
        self._tasks: Dict[str, asyncio.Task[Any]] = {}
        self.suspend_queue: Deque[HITLSuspension] = deque()
        self._by_run_tool: Dict[Tuple[str, str], HITLSuspension] = {}
        self.events: List[Dict[str, Any]] = []

    def _require_approval_tools(self, harness: Any) -> List[str]:
        tools: List[str] = []
        hcfg = getattr(harness, "harness_config", None) or {}
        ccfg = getattr(harness, "context_config", None) or {}
        correct_cfg = hcfg.get("correct", {}) or {}
        tools.extend(list(correct_cfg.get("require_approval", []) or []))
        constrain_cfg = ccfg.get("constrain", {}) or ccfg.get("constraints", {}) or {}
        tools.extend(list(constrain_cfg.get("require_approval", []) or []))
        out: List[str] = []
        for t in tools:
            if isinstance(t, str) and t and t not in out:
                out.append(t)
        return out

    async def submit(self, req: WorkflowRequest) -> str:
        run_id = req.run_id or os.urandom(8).hex()
        harness = req.harness
        user_input = (req.inputs or {}).get("user_input") or (req.inputs or {}).get("query") or ""

        async def _task() -> Any:
            require_approval_set = set(self._require_approval_tools(harness))
            trace = harness._trace
            # v2 版 Harness 初始化 _trace
            if trace is None and hasattr(harness, "run"):
                trace = await harness.run(user_input)
                self.traces[run_id] = trace
                return trace
            max_turns = int(getattr(harness, "max_turns", 3) or 3)
            for _ in range(max_turns):
                # 在 _react_step 之前：用 v2 接口先看 turn.action 是否命中 require_approval
                # 直接把 Harness 的 _react_step 包一层：注册 approve/reject 钩子
                if require_approval_set:
                    async def _wrapped_react_step(orig_step_fn):
                        # 先把 action 从下一个要调用的 turn 里预读？更稳的方法是在 constrain 之后 execute 前：
                        # 这里简化：用 status_bar events 反查（但 status_bar 是可观测，不提供 action pre-hook）
                        # 最终方法：把 harness.constrain 包一层 Wrapper
                        return await orig_step_fn()
                    _ = _wrapped_react_step  # 占位；真实路径用另一种：直接跑 run()，在 constrain 里通过 side channel 抛 HITLNeedApproval
                result = await harness._react_step() if hasattr(harness, "_react_step") else None
                if result is None:
                    break
                st = result.get("status")
                if st in ("success", "failed", "blocked", "human_required"):
                    break
            self.traces[run_id] = harness._trace
            return harness._trace

        async def _task_via_run() -> Any:
            """为了不依赖 turn.action 的先验，直接在 Constrain 阶段注入 Hook：
            monkeypatch harness.constrain → 命中 require_approval 时放 suspension。"""
            require_approval_set = set(self._require_approval_tools(harness))
            orig_constrain = harness.constrain
            run_state: Dict[str, Any] = {"active_suspension": None}

            def _emit_event(kind: str, **extra: Any) -> None:
                self.events.append({"run_id": run_id, "kind": kind, **extra})
                try:
                    sb = getattr(harness, "status_bar", None)
                    if sb is not None and hasattr(sb, "on_step"):
                        sb.on_step(run_id, len(getattr(harness, "_trace", None).turns if harness._trace else []), kind, str(extra))
                except Exception:  # noqa: BLE001
                    pass

            def _hooked_constrain(tool_call):
                nonlocal run_state
                allowed, reason = orig_constrain(tool_call)
                tool_name = tool_call.get("tool_name", "") if isinstance(tool_call, dict) else ""
                if not require_approval_set:
                    return allowed, reason
                if tool_name in require_approval_set and allowed:
                    args = tool_call.get("args", {}) if isinstance(tool_call, dict) else {}
                    susp = HITLSuspension(run_id=run_id, tool_name=tool_name, args=args)
                    self.suspend_queue.append(susp)
                    self._by_run_tool[(run_id, tool_name)] = susp
                    run_state["active_suspension"] = susp
                    _emit_event("human_required", tool_name=tool_name, args=args)
                    # 同步等待审批（在 asyncio 事件循环里：必须改为 yield）。简化：抛 HITLNeedApproval 并在 catch 里 await。
                    raise _HITLNeedApproval(susp)
                return allowed, reason

            harness.constrain = _hooked_constrain  # type: ignore[method-assign]
            try:
                while True:
                    try:
                        trace = await harness.run(user_input)
                        self.traces[run_id] = trace
                        return trace
                    except _HITLNeedApproval as hitl_exc:
                        susp = hitl_exc.suspension
                        # 等待 approve/reject
                        await asyncio.wait_for(susp.approvable_event.wait(), timeout=86_400.0)
                        if susp.decision == "reject":
                            self.events.append({"run_id": run_id, "kind": "human_rejected", "tool_name": susp.tool_name})
                            try:
                                harness.status_bar.on_step(run_id, len(harness._trace.turns) if harness._trace else 0, "rejected", susp.tool_name)
                            except Exception:  # noqa: BLE001
                                pass
                            # 将 trace.status 置 failed + error=human_rejected
                            if harness._trace is not None:
                                setattr(harness._trace, "status", "failed")
                                setattr(harness._trace, "error", f"human_rejected: tool={susp.tool_name}")
                            return harness._trace
                        assert susp.decision == "approve"
                        self.events.append({"run_id": run_id, "kind": "human_approved", "tool_name": susp.tool_name})
                        # 继续下一循环，此时再次调用 constrain → 同一个 tool_name 会再次命中 require_approval，需要放行一次：
                        # 使用 allow_once set
                        require_approval_set.discard(susp.tool_name)
                        continue
            finally:
                harness.constrain = orig_constrain  # type: ignore[method-assign]

        self._tasks[run_id] = asyncio.create_task(_task_via_run())
        return run_id

    async def wait(self, run_id: str, timeout: float = 300.0) -> Any:
        if run_id in self.traces:
            return self.traces[run_id]
        task = self._tasks.get(run_id)
        if task is None:
            raise KeyError(f"no run_id: {run_id}")
        trace = await asyncio.wait_for(task, timeout=timeout)
        return trace

    async def approve(self, run_id: str, tool_name: str) -> None:
        key = (run_id, tool_name)
        susp = self._by_run_tool.get(key)
        if susp is None:
            # 兼容：等一会儿让事件产生（HITL suspend 是异步入队的）
            deadline = asyncio.get_running_loop().time() + 5.0
            while asyncio.get_running_loop().time() < deadline:
                susp = self._by_run_tool.get(key)
                if susp is not None:
                    break
                await asyncio.sleep(0.05)
        if susp is None:
            raise KeyError(f"no suspension for run_id={run_id} tool={tool_name}")
        susp.resolve("approve")

    async def reject(self, run_id: str, tool_name: str) -> None:
        key = (run_id, tool_name)
        susp = self._by_run_tool.get(key)
        if susp is None:
            deadline = asyncio.get_running_loop().time() + 5.0
            while asyncio.get_running_loop().time() < deadline:
                susp = self._by_run_tool.get(key)
                if susp is not None:
                    break
                await asyncio.sleep(0.05)
        if susp is None:
            raise KeyError(f"no suspension for run_id={run_id} tool={tool_name}")
        susp.resolve("reject")


class _HITLNeedApproval(Exception):
    def __init__(self, suspension: HITLSuspension) -> None:
        super().__init__(f"HITL approve needed: tool={suspension.tool_name}")
        self.suspension = suspension


class TemporalRunner(WorkflowRunner):
    """Durable execution via Temporal. Requires `uv pip install 'agentlisp[durable]'`."""

    def __init__(
        self,
        *,
        temporal_client: Optional[Any] = None,
        task_queue: str = "agentlisp",
        namespace: str = "default",
        host_port: str = "localhost:7233",
    ) -> None:
        try:
            import temporalio  # noqa: F401  # type: ignore[import-not-found]
        except ImportError as exc:
            raise FeatureNotInstalledError("Temporal runner", "durable") from exc
        self._client = temporal_client
        self.task_queue = task_queue
        self.namespace = namespace
        self.host_port = host_port

    async def _get_client(self) -> Any:  # pragma: no cover - temporal not in CI env
        if self._client is None:
            from temporalio.client import Client  # type: ignore[import-not-found]
            self._client = await Client.connect(
                target_url=self.host_port, namespace=self.namespace
            )
        return self._client

    async def submit(self, req: WorkflowRequest) -> str:  # pragma: no cover
        raise NotImplementedError(
            "TemporalRunner.submit skeleton: wire Harness.run_async into a Temporal workflow "
            "once your durable workflow/activities are defined."
        )

    async def wait(self, run_id: str, timeout: float = 300.0) -> ExecutionTrace:  # pragma: no cover
        raise NotImplementedError("TemporalRunner.wait skeleton")


def default_runner(prefer_temporal: Optional[bool] = None) -> WorkflowRunner:
    want = prefer_temporal if prefer_temporal is not None else (
        os.getenv("AGENTLISP_RUNNER", "direct").lower() == "temporal"
    )
    if want:
        try:
            return TemporalRunner()
        except FeatureNotInstalledError:
            pass
    return DirectRunner()


__all__ = [
    "WorkflowRequest",
    "WorkflowRunner",
    "DirectRunner",
    "InMemoryHITLRunner",
    "TemporalRunner",
    "default_runner",
]

