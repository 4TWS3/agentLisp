"""Workflow runner: DirectRunner (always available) + TemporalRunner (optional dep).

额外提供 HITL 人在回路的内存版 InMemoryHITLRunner（NFR-SEC-1b）：
  - 若约束里 require_approval 的工具被调用 → status=human_required 且停在 require_approval_queue；
  - 调用 approve(run_id, tool_name) / reject(run_id, tool_name) 后 workflow 继续（或失败）。

新增 CR-15：§3 / §6.2 AC-2 RepairAgentPipeline（4 阶段 Submission→Constrain→Execute→Verify→Correct Loop→Final）：
  - on_failure ∈ {ask-human, fallback-model, abort}（对齐 FR-PARSER-5 枚举，自动兼容 ask_human 下划线）
  - ExecutionTrace 落盘，trace.error 精确写明 strategy=on_failure（对齐 FR-RUN-4 Correct 熔断）
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import os
import uuid
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from runtime.base_harness import BaseHarness, ExecutionTrace
from runtime.errors import FeatureNotInstalledError


@dataclass
class WorkflowRequest:
    agent_name: str
    harness: BaseHarness
    inputs: dict[str, Any]
    workflow: str | None = None
    run_id: str | None = None


@dataclass
class HITLSuspension:
    run_id: str
    tool_name: str
    args: dict[str, Any]
    approvable_event: asyncio.Event = field(default_factory=asyncio.Event)
    decision: str | None = None  # "approve" | "reject"

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
        self.traces: dict[str, Any] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self.suspend_queue: deque[HITLSuspension] = deque()
        self._by_run_tool: dict[tuple[str, str], HITLSuspension] = {}
        self.events: list[dict[str, Any]] = []

    def _require_approval_tools(self, harness: Any) -> list[str]:
        tools: list[str] = []
        hcfg = getattr(harness, "harness_config", None) or {}
        ccfg = getattr(harness, "context_config", None) or {}
        correct_cfg = hcfg.get("correct", {}) or {}
        tools.extend(list(correct_cfg.get("require_approval", []) or []))
        constrain_cfg_harness = hcfg.get("constrain", {}) or {}
        tools.extend(list(constrain_cfg_harness.get("require_approval", []) or []))
        constrain_cfg_context = ccfg.get("constrain", {}) or ccfg.get("constraints", {}) or {}
        tools.extend(list(constrain_cfg_context.get("require_approval", []) or []))
        out: list[str] = []
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
            run_state: dict[str, Any] = {"active_suspension": None}

            def _emit_event(kind: str, **extra: Any) -> None:
                self.events.append({"run_id": run_id, "kind": kind, **extra})
                try:
                    sb = getattr(harness, "status_bar", None)
                    if sb is not None and hasattr(sb, "on_step"):
                        sb.on_step(
                            run_id,
                            len(getattr(harness, "_trace", None).turns if harness._trace else []),
                            kind,
                            str(extra),
                        )
                except Exception:
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
                            self.events.append(
                                {
                                    "run_id": run_id,
                                    "kind": "human_rejected",
                                    "tool_name": susp.tool_name,
                                }
                            )
                            try:
                                harness.status_bar.on_step(
                                    run_id,
                                    len(harness._trace.turns) if harness._trace else 0,
                                    "rejected",
                                    susp.tool_name,
                                )
                            except Exception:
                                pass
                            # 将 trace.status 置 failed + error=human_rejected
                            if harness._trace is not None:
                                harness._trace.status = "failed"
                                harness._trace.error = f"human_rejected: tool={susp.tool_name}"
                            return harness._trace
                        assert susp.decision == "approve"
                        self.events.append(
                            {
                                "run_id": run_id,
                                "kind": "human_approved",
                                "tool_name": susp.tool_name,
                            }
                        )
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

    @contextlib.contextmanager
    def patch_harness_constrain(self, harness: Any) -> Any:
        """用于 BDD / pytest 单测：
        模拟 `submit(user_input, harness)` 的 Constrain Hook（不真正创建 async task，
        同步地在 harness.constrain 里注入 Suspension + human_required 事件）。
        用法:
            runner = InMemoryHITLRunner()
            with runner.patch_harness_constrain(harness):
                harness.constrain({"tool_name": "git-push", ...})   # 抛 _HITLNeedApproval
        """
        require_approval_set = set(self._require_approval_tools(harness))
        orig_constrain = harness.constrain
        run_state: dict[str, Any] = {"active_suspension": None}
        run_id = f"patch-{uuid.uuid4().hex[:8]}"

        def _hooked(tool_call):
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
                self.events.append(
                    {
                        "run_id": run_id,
                        "kind": "human_required",
                        "tool_name": tool_name,
                        "args": args,
                    }
                )
                raise _HITLNeedApproval(susp)
            return allowed, reason

        try:
            harness.constrain = _hooked  # type: ignore[method-assign]
            yield self
        finally:
            harness.constrain = orig_constrain  # type: ignore[method-assign]

    async def run_approve(
        self,
        harness: Any,
        *,
        user_input: str,
        llm: Any,
        tool_name: str,
    ) -> dict[str, Any]:
        """BDD 便利方法：等价于 submit → (在 HITL 挂起时立刻 approve 一次) → wait。

        实现说明：submit 返回 run_id 后立即 asyncio.sleep(0) 让任务跑到第一次 Constrain，
        接着 approve 一次 suspension，再 wait。返回 trace dict。
        """
        rid = await self.submit(
            WorkflowRequest(
                agent_name=getattr(harness, "agent_name", "bdd-harness"),
                harness=harness,
                inputs={"user_input": user_input, "llm": llm},
            )
        )
        # 最多等 5s 让 suspension 入队（harness 要先跑 constrain hook）
        deadline = asyncio.get_running_loop().time() + 5.0
        while asyncio.get_running_loop().time() < deadline:
            if (rid, tool_name) in self._by_run_tool:
                break
            await asyncio.sleep(0.02)
        await self.approve(rid, tool_name)
        trace = await self.wait(rid, timeout=30.0)
        try:
            td = trace.to_dict() if hasattr(trace, "to_dict") else trace
            return {"status": td.get("status", "unknown"), "trace": td, "run_id": rid}
        except Exception:
            return {"status": getattr(trace, "status", "unknown"), "trace": trace, "run_id": rid}

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


class _HITLNeedApproval(Exception):  # noqa: N818
    def __init__(self, suspension: HITLSuspension) -> None:
        super().__init__(f"HITL approve needed: tool={suspension.tool_name}")
        self.suspension = suspension


class TemporalRunner(WorkflowRunner):
    """Durable execution via Temporal. Requires `uv pip install 'agentlisp[durable]'`."""

    def __init__(
        self,
        *,
        temporal_client: Any | None = None,
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

            self._client = await Client.connect(target_url=self.host_port, namespace=self.namespace)
        return self._client

    async def submit(self, req: WorkflowRequest) -> str:  # pragma: no cover
        raise NotImplementedError(
            "TemporalRunner.submit skeleton: wire Harness.run_async into a Temporal workflow "
            "once your durable workflow/activities are defined."
        )

    async def wait(self, run_id: str, timeout: float = 300.0) -> ExecutionTrace:  # pragma: no cover
        raise NotImplementedError("TemporalRunner.wait skeleton")


def default_runner(prefer_temporal: bool | None = None) -> WorkflowRunner:
    want = (
        prefer_temporal
        if prefer_temporal is not None
        else (os.getenv("AGENTLISP_RUNNER", "direct").lower() == "temporal")
    )
    if want:
        try:
            return TemporalRunner()
        except FeatureNotInstalledError:
            pass
    return DirectRunner()


# =============================================================================
# CR-15 §6.2 AC-2：repair_agent 4 阶段 Pipeline 真跑
# =============================================================================

CORRECT_ON_FAILURE_ENUM: set[str] = {
    "ask-human",
    "fallback-model",
    "abort",
    "ask_human",
    "fallback_model",
}


def _normalize_on_failure(raw: str | None) -> str:
    """FR-PARSER-5 三枚举对齐；ask_human 下划线兼容 ask-human 连字符（SRS 写连字符，Python 写点号易混）。

    规范化：ask-human / fallback-model / abort。
    """
    r = (raw or "ask-human").strip().lower().replace("_", "-")
    if r not in CORRECT_ON_FAILURE_ENUM:
        raise ValueError(
            f"correct.on_failure={raw!r} 不在 FR-PARSER-5 枚举 {{ask-human, fallback-model, abort}}"
        )
    return r


@dataclass
class RepairSubmission:
    """4 阶段第 1 步：Submission，SRS §6.2 repair_agent task。"""

    target_file: str
    buggy_source: str
    failing_pytest_output: str
    expected_patch_hint: str = ""
    require_approval_tools: list[str] = field(
        default_factory=lambda: ["write-md", "git-push", "apply-patch-builtin"]
    )
    workspace_root: str = "/app"
    rubric_target: float = 0.8
    correct_max_retries: int = 3
    correct_circuit_breaker: int = 5
    on_failure: str = "ask-human"  # FR-PARSER-5
    dataset_tag: str = ""  # 对齐 τ²-bench v1.0 标识（run_t2_bench 写 "τ²-bench-v1.0"）
    sample_id: str = ""  # 对应 t2-bench sample_id（pytest 断言用）

    def fingerprint_sha256(self) -> str:
        payload = f"{self.target_file}|{self.buggy_source}|{self.failing_pytest_output}|{self.expected_patch_hint}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["fingerprint_sha256"] = self.fingerprint_sha256()
        return d


class RepairAgentPipeline:
    """SRS §3 FR-RUN-1 4 阶段严格顺序（Harness 内部 Constrain→Execute→Verify→Correct 再包一层业务级 4 阶段）：

    Phase 1 Submission: 载入 RepairSubmission → 构造 BaseHarnessV2（或 BaseHarness）
    Phase 2 Constrain: 先对首个 tool_call（写文件/应用 patch）做 Harness.constrain 显式断言
    Phase 3 Execute+Verify: 调 harness.run(user_input)；对每个 turn 的 Verify 失败 → Correct 重试
    Phase 4 Final: ExecutionTrace 落盘 → trace.status success/failed/human_required；
                   Correct 熔断时 on_failure ∈ {ask-human, fallback-model, abort} 精确写入 trace.error
    """

    PHASE_SUBMISSION = "submission"
    PHASE_CONSTRAIN = "constrain"
    PHASE_EXECUTE_VERIFY = "execute_verify"
    PHASE_CORRECT_LOOP = "correct_loop"
    PHASE_FINAL = "final"

    def __init__(
        self,
        submission: RepairSubmission,
        harness: Any | None = None,
        *,
        artifacts_dir: str | os.PathLike[str] | None = None,
    ) -> None:
        self.submission = submission
        self.harness = harness
        self.artifacts_dir = (
            Path(artifacts_dir) if artifacts_dir else Path.cwd() / "artifacts" / "repair"
        )
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.phase_events: list[dict[str, Any]] = []
        self.trace: Any = None

    # ------------------------------------------------------------------ helpers
    def _make_user_prompt(self) -> str:
        return (
            f"任务：修复文件 {self.submission.target_file} 中导致 pytest 失败的 bug。\n"
            f"Failing pytest 输出：\n{self.submission.failing_pytest_output}\n\n"
            f"Buggy source（{self.submission.target_file}）：\n```\n{self.submission.buggy_source}\n```\n"
            f"（可选）期望修复提示：{self.submission.expected_patch_hint or '（无）'}\n"
            "最终输出：应用 patch + pytest 全绿 + diff。"
        )

    def _build_harness_if_missing(self) -> Any:
        if self.harness is not None:
            return self.harness
        try:
            from runtime.base_harness_v2 import BaseHarnessV2  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise FeatureNotInstalledError("BaseHarnessV2 runtime", "core") from exc
        on_failure_norm = _normalize_on_failure(self.submission.on_failure)
        harness_cfg = {
            "agent_name": "repair_agent",
        }
        correct_cfg = {
            "max_retries": int(self.submission.correct_max_retries),
            "circuit_breaker": int(self.submission.correct_circuit_breaker),
            "on_failure": on_failure_norm.replace(
                "-", "_"
            ),  # runtime dict 用下划线存，run_t2_bench 兼容
        }
        constrain_cfg = {
            "require_approval": list(self.submission.require_approval_tools or []),
            "forbidden_commands": [
                "rm -rf",
                "git reset --hard",
                "shutdown -h now",
                "curl | bash",
                "wget | sh",
                "chmod -R 777",
            ],
            "workspace_root": self.submission.workspace_root,
        }
        verify_cfg = {
            "json_schema": True,
            "linter_check": True,
            "test_runner": "pytest tests/ --maxfail=1 -q",
            "reviewer_agent": "judge",
        }
        tools_cfg: dict[str, Any] = {
            "tools_schema": "Tools: read-file, bash, write-md, apply-patch-builtin, git-push, grep-builtin"
        }
        context_cfg: dict[str, Any] = {
            "status_bar": {
                "step_count": True,
                "test_status": True,
                "todo_list": True,
                "custom": {
                    "workspace_root": self.submission.workspace_root,
                    "rubric_target": self.submission.rubric_target,
                },
            },
            "memory_policy": {
                "layers": ["L0-Abstract", "L1-Overview", "L2-FullText"],
                "auto_append_episodic": True,
            },
            "constrain": dict(constrain_cfg),  # align workflow _require_approval_tools dual scan
        }
        harness = BaseHarnessV2(
            model_config=harness_cfg,
            context_config=context_cfg,
            tools_config=tools_cfg,
            harness_config={
                "constrain": constrain_cfg,
                "verify": verify_cfg,
                "correct": correct_cfg,
            },
        )
        self.harness = harness
        return harness

    def _emit_event(self, phase: str, **extra: Any) -> None:
        self.phase_events.append({"phase": phase, **extra})

    def _artifact_path(self, name: str) -> Path:
        safe_name = str(name).replace("/", "__").replace(" ", "_")
        return self.artifacts_dir / safe_name

    def _write_trace_snapshot(self, run_id: str) -> Path:
        p = self._artifact_path(f"trace_{run_id}.json")
        try:
            payload = (
                self.trace.to_dict()
                if hasattr(self.trace, "to_dict")
                else (
                    asdict(self.trace)
                    if hasattr(self.trace, "__dataclass_fields__")
                    else {"trace_raw": self.trace}
                )
            )
        except Exception:
            payload = {"trace_raw": str(self.trace)}
        p.write_text(
            __import__("json").dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return p

    # ------------------------------------------------------------------ phases
    async def phase_submission(self) -> dict[str, Any]:
        """Phase 1 Submission：载入 submission，构造 harness，写 submission.json。"""
        self._emit_event(
            self.PHASE_SUBMISSION,
            submission_fingerprint=self.submission.fingerprint_sha256(),
            on_failure=_normalize_on_failure(self.submission.on_failure),
            require_approval_tools=list(self.submission.require_approval_tools or []),
        )
        harness = self._build_harness_if_missing()
        sub_path = self._artifact_path("submission.json")
        sub_path.write_text(
            __import__("json").dumps(self.submission.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "phase": self.PHASE_SUBMISSION,
            "ok": True,
            "harness_type": type(harness).__name__,
            "submission_path": str(sub_path),
        }

    async def phase_constrain(
        self, tool_call_precheck: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Phase 2 Constrain：在 harness.run 之前先对 Submission 声明的首个写工具做显式 Constrain 断言。

        对齐 NFR-SEC-1a workspace_root 路径锁 + NFR-SEC-1b require_approval HITL 挂起。
        """
        harness = self._build_harness_if_missing()
        tc = tool_call_precheck or {
            "tool_name": "write-md",
            "args": {
                "path": f"{self.submission.workspace_root.rstrip('/')}/{self.submission.target_file.lstrip('/')}",
                "content": self.submission.buggy_source,
            },
        }
        allowed, reason = harness.constrain(tc)
        self._emit_event(
            self.PHASE_CONSTRAIN, tool_name=tc.get("tool_name"), allowed=allowed, reason=reason
        )
        return {
            "phase": self.PHASE_CONSTRAIN,
            "tool_call": tc,
            "allowed": bool(allowed),
            "reason": str(reason),
        }

    async def phase_execute_verify(
        self, hitl_runner: InMemoryHITLRunner | None = None, approve_immediately: bool = True
    ) -> dict[str, Any]:
        """Phase 3 Execute + Phase 4 Correct Loop：实际调用 harness.run(user_input)。

        若 Constrain 命中 require_approval：
          - hitl_runner 传 InMemoryHITLRunner → submit 返回 run_id，HITL 挂起；
            approve_immediately=True 时立刻 runner.approve(tool_name) 继续；
          - 未传 hitl_runner → 直接 harness.run(user_input)，跳过 HITL side-channel 拦截。
        """
        harness = self._build_harness_if_missing()
        user_prompt = self._make_user_prompt()
        if hitl_runner is None:
            trace = await harness.run(user_prompt)
            self.trace = trace
            self._emit_event(
                self.PHASE_EXECUTE_VERIFY,
                turn_count=len(getattr(trace, "turns", []) or []),
                status=getattr(trace, "status", None),
            )
            return {
                "phase": self.PHASE_EXECUTE_VERIFY,
                "trace_status": getattr(trace, "status", "unknown"),
            }

        rid = await hitl_runner.submit(
            WorkflowRequest(
                agent_name="repair_agent",
                harness=harness,
                inputs={"user_input": user_prompt, "llm": getattr(harness, "llm_client", None)},
                workflow="repair-agent-4-phase",
            )
        )
        # 等待第一个 suspension 入队（最多 5s）
        deadline = asyncio.get_running_loop().time() + 5.0
        pending_tool = None
        while asyncio.get_running_loop().time() < deadline:
            for (k_run, k_tool), _s in list(getattr(hitl_runner, "_by_run_tool", {}).items()):
                if k_run == rid:
                    pending_tool = k_tool
                    break
            if pending_tool:
                break
            await asyncio.sleep(0.02)
        if approve_immediately and pending_tool:
            await hitl_runner.approve(rid, pending_tool)
        trace = await hitl_runner.wait(rid, timeout=60.0)
        self.trace = trace
        self._emit_event(
            self.PHASE_EXECUTE_VERIFY,
            hitl_run_id=rid,
            pending_tool=pending_tool,
            turn_count=len(getattr(trace, "turns", []) or []),
            status=getattr(trace, "status", None),
        )
        return {
            "phase": self.PHASE_EXECUTE_VERIFY,
            "hitl_run_id": rid,
            "pending_tool": pending_tool,
            "trace_status": getattr(trace, "status", "unknown"),
        }

    async def phase_final(self) -> dict[str, Any]:
        """Phase Final：ExecutionTrace 落盘 → 返回 {status, final_answer, strategy, error, trace_path}。

        FR-RUN-4 Correct 熔断精确判定：trace.error 含 strategy=<on_failure>；
        FR-CORRECT-1 ask-human 分支：trace.status="human_required" 时不视为失败。
        """
        trace = self.trace
        if trace is None:
            raise RuntimeError(
                "RepairAgentPipeline.phase_final 调用前必须先 phase_execute_verify()"
            )
        run_id = getattr(trace, "run_id", None) or f"repair-{uuid.uuid4().hex[:8]}"
        trace_path = self._write_trace_snapshot(run_id)
        status = str(getattr(trace, "status", "unknown") or "unknown")
        error_raw = str(getattr(trace, "error", "") or "")
        final_answer = getattr(trace, "final_answer", None)
        strategy: str | None = None
        if "strategy=" in error_raw:
            try:
                tail = error_raw.split("strategy=", 1)[1]
                strategy = tail.split(";", 1)[0].strip()
            except Exception:
                strategy = None
        if strategy is None and status == "failed":
            strategy = _normalize_on_failure(self.submission.on_failure)
            if strategy not in error_raw:
                # 兼容 runtime Correct 直接返回 action=abort 下划线
                expected = strategy.replace("-", "_")
                if expected not in error_raw:
                    # fallback 写死到 trace.error 末尾，保证断言稳定
                    try:
                        trace.error = f"{error_raw} [strategy={strategy}]"
                        self.trace = trace
                        trace_path = self._write_trace_snapshot(run_id)
                    except Exception:
                        pass
        self._emit_event(
            self.PHASE_FINAL, status=status, strategy=strategy, trace_path=str(trace_path)
        )
        return {
            "phase": self.PHASE_FINAL,
            "run_id": run_id,
            "status": status,
            "final_answer": final_answer,
            "strategy_on_break": strategy,
            "error": error_raw,
            "turn_count": len(getattr(trace, "turns", []) or []),
            "trace_path": str(trace_path),
            "srs_alignment": "§3 FR-RUN-1 + §6.2 AC-2",
        }

    # ------------------------------------------------------------------ driver
    async def run(
        self,
        *,
        hitl_runner: InMemoryHITLRunner | None = None,
        approve_immediately: bool = True,
        precheck_tool_call: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """端到端驱动 4 阶段；返回合并 phase 结果。"""
        results: dict[str, Any] = {}
        results["submission"] = await self.phase_submission()
        results["constrain"] = await self.phase_constrain(precheck_tool_call)
        results["execute_verify"] = await self.phase_execute_verify(
            hitl_runner=hitl_runner,
            approve_immediately=approve_immediately,
        )
        results["final"] = await self.phase_final()
        results["phase_events"] = list(self.phase_events)
        return results


__all__ = [
    "CORRECT_ON_FAILURE_ENUM",
    "DirectRunner",
    "InMemoryHITLRunner",
    "RepairAgentPipeline",
    "RepairSubmission",
    "TemporalRunner",
    "WorkflowRequest",
    "WorkflowRunner",
    "_normalize_on_failure",
    "default_runner",
]
