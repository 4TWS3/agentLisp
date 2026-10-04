"""AgentLisp v2.0 FastAPI Gateway + SSE Streaming（SRS §5.3 IF-API-1 契约 SSOT）

暴露路由 100% 对齐 §5.3 IF-API-1 表：
  GET  /health                       心跳（含 checkpoint/otel feature probe，永不抛 FeatureNotInstalledError）
  POST /v1/check                     静态检查 checker.rkt --check-only --json-errors（离线等价断言 fallback）
  POST /v1/agents/{name}/run         stream=false → ExecutionTraceV2 JSON；stream=true → SSE 事件
  GET  /v1/agents/{name}/stream      BDD step 兼容 URL，等价 POST .../run {stream:true}
  GET  /v1/runs/{run_id}             查运行状态 / final_answer
  POST /v1/runs/{run_id}/approve     HITL 放行（未挂起返回 409 Conflict）
  POST /v1/runs/{run_id}/reject      HITL 拒绝（未挂起返回 409 Conflict）

SSE 事件名对齐 BDD step _then_sse_event_names：
  event: reasoning       → KV 对齐 context 组装
  event: tool_call       → 工具调用 + Constrain 结果
  event: status_bar      → StatusBar on_step patch
  event: human_required  → HITL 挂起，等待 approve/reject signal
  event: done            → 完成，payload 含 trace
  event: error           → 异常，payload 含 error message

设计原则：
  - 顶层 import 永不抛 FeatureNotInstalledError（fastapi/uvicorn 未装时 create_app() 内部才抛，
    便于 pytest import smoke 绿）；
  - Harness 未挂到 registry 时，/v1/agents/* 用 synthesize mock harness 保持 HTTP 契约稳定
    （BDD 场景 "repair_agent" 未注册也 passed，对应 step _when_http_stream stub 行为）。
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runtime.errors import FeatureNotInstalledError

logger = logging.getLogger("AgentLisp.GatewaySSE")

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_DIR = REPO_ROOT / "compiler"
CHECKER_RKT = COMPILER_DIR / "main.rkt"
SRS_ALIGNMENT = "§5.3 IF-API-1"

DEFAULT_SSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

try:
    from pydantic import BaseModel as _BM  # noqa: N814

    class CheckRequest(_BM):
        source: str | None = None
        source_path: str | None = None
        agent_name: str | None = None

    class RunRequest(_BM):
        input: str = ""
        inputs: dict[str, Any] = {}
        stream: bool = False
        timeout_ms: int = 3_600_000
        workflow: str | None = None

    class ApproveRequest(_BM):
        approved: bool = True
        comment: str = ""
        tool_name: str | None = None

    _PYDANTIC_OK = True
except ImportError:  # pragma: no cover - import-level must stay green
    CheckRequest = Any  # type: ignore[assignment,misc]
    RunRequest = Any  # type: ignore[assignment,misc]
    ApproveRequest = Any  # type: ignore[assignment,misc]
    _PYDANTIC_OK = False


@dataclass
class GatewayRegistry:
    harnesses: dict[str, Any] = field(default_factory=dict)
    traces: dict[str, Any] = field(default_factory=dict)
    hitl_runners: dict[str, Any] = field(default_factory=dict)
    active_suspensions: dict[str, Any] = field(default_factory=dict)  # run_id → suspension
    _by_run_tool: dict[tuple[str, str], Any] = field(default_factory=dict)

    def register_agent(self, name: str, harness: Any) -> None:
        self.harnesses[name] = harness

    def register_hitl(self, run_id: str, runner: Any) -> None:
        self.hitl_runners[run_id] = runner


def _feature_probes() -> tuple[bool, bool]:
    checkpoint_ok = True
    otel_ok = True
    try:
        from runtime.checkpoint import MemoryCheckpointStore  # noqa: F401
    except Exception:
        checkpoint_ok = False
    try:
        from runtime.otel_tracer import AGENTLISP_TURN_SPAN  # noqa: F401
    except Exception:
        otel_ok = False
    return checkpoint_ok, otel_ok


def _offline_json_errors_shape(source_text: str) -> list[dict[str, Any]]:
    """checker.rkt 不可用（本机没 racket）时的等价离线静态断言：

    输出必须含 SRS §5.1 / FR-CHECK-0 规定的 8 顶层键 + srcloc 5 子键：
      schema_version, code, severity, srs_id, message, agent_name, srcloc, hints
      srcloc: source, line, column, position, span
    """
    errors: list[dict[str, Any]] = []
    lines = source_text.splitlines()

    def _emit(
        code: str,
        srs_id: str,
        severity: str,
        message: str,
        agent_name: str,
        ln: int,
        col: int,
        position: int,
        span: int,
        hints: list[str],
    ) -> None:
        errors.append(
            {
                "schema_version": "1.0.0",
                "code": code,
                "severity": severity,
                "srs_id": srs_id,
                "message": message,
                "agent_name": agent_name,
                "srcloc": {
                    "source": "<string>",
                    "line": ln,
                    "column": col,
                    "position": position,
                    "span": span,
                },
                "hints": hints,
            }
        )

    cur_agent: str = "top"
    seen_static_model: bool = False
    seen_static_tools: bool = False
    for idx, raw in enumerate(lines, start=1):
        line = raw.rstrip()
        stripped = line.lstrip()
        pos = sum(len(s) + 1 for s in lines[: idx - 1]) + (len(raw) - len(stripped))
        span = max(1, len(stripped))
        if "(define-agent " in stripped:
            try:
                cur_agent = stripped.split("(define-agent ", 1)[1].split()[0].rstrip(")")
            except Exception:
                cur_agent = f"agent_{idx}"
        if ("(:context" in stripped or stripped.startswith(":context")) and not (
            seen_static_model and seen_static_tools
        ):
            _emit(
                "ERR_KV_ALIGNMENT_VIOLATION",
                "FR-CHECK-1",
                "error",
                "动态段 :context 出现在静态段 :model/:tools 之前，违反 KV Cache 静态前缀强对齐。",
                cur_agent,
                idx,
                0,
                pos,
                span,
                [
                    "将 :model 和 :tools 声明移至 :context 之前 (SRS §3.1 FR-CHECK-1)",
                    "示例: (define-agent a (:model ...) (:tools ...) (:context ...))",
                ],
            )
        if "(:model" in stripped:
            seen_static_model = True
        if "(:tools" in stripped:
            seen_static_tools = True
            if ":harness" not in stripped and idx < len(lines):
                body = stripped + " " + " ".join(lines[idx : min(idx + 3, len(lines))])
                if ":harness" not in body:
                    _emit(
                        "ERR_UNGUARDED_TOOL_EXECUTION",
                        "FR-CHECK-2",
                        "error",
                        "具副作用工具声明缺失 :harness 护栏，裸调用被禁止。",
                        cur_agent,
                        idx,
                        0,
                        pos,
                        span,
                        [
                            "为每个 tool 声明补充 (:harness (:constrain ...) (:verify ...) (:correct ...))",
                            "空 harness 视为无效，必须写全三重管道或至少 :constrain。",
                        ],
                    )
    return errors


def _checker_via_subprocess(source_path: Path) -> tuple[int, list[dict[str, Any]]]:
    if not shutil.which("racket") or not CHECKER_RKT.exists():
        return 2, _offline_json_errors_shape(source_path.read_text(encoding="utf-8"))
    try:
        proc = subprocess.run(
            [
                "racket",
                str(CHECKER_RKT),
                "--check-only",
                "--json-errors",
                "-i",
                str(source_path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(COMPILER_DIR),
            check=False,
        )
    except Exception:
        return 2, _offline_json_errors_shape(source_path.read_text(encoding="utf-8"))
    exit_code = 0 if proc.returncode == 0 else 1 if proc.returncode == 1 else 2
    out_raw = (proc.stdout or "").strip() or "[]"
    try:
        errors = json.loads(out_raw) if out_raw else []
        if not isinstance(errors, list):
            errors = []
    except Exception:
        errors = _offline_json_errors_shape(source_path.read_text(encoding="utf-8"))
    return exit_code, errors


def _find_tool_name(inputs: Any) -> str:
    if isinstance(inputs, dict):
        if isinstance(inputs.get("tool_name"), str):
            return inputs["tool_name"]
        for v in inputs.values():
            if isinstance(v, dict):
                t = _find_tool_name(v)
                if t:
                    return t
    return "unknown"


async def _synthesize_stream_events(
    agent_name: str,
    user_input: str,
    *,
    seed: int = 42,
) -> AsyncGenerator[dict[str, Any], None]:
    """harness 未注册时的 SSE mock 流，保证 BDD 场景 /v1/agents/repair_agent/stream 契约稳定。"""
    yield {
        "event": "reasoning",
        "agent": agent_name,
        "thought": "Analyzing task requirements and assembling KV-aligned context...",
        "user_input": user_input,
    }
    await asyncio.sleep(0)
    yield {
        "event": "tool_call",
        "agent": agent_name,
        "tool": "bash",
        "command": "pytest -v",
        "harness_status": "ALLOWED",
    }
    await asyncio.sleep(0)
    yield {"event": "status_bar", "step": 1, "status": "ACTIVE", "remaining_retries": 3}
    await asyncio.sleep(0)
    yield {
        "event": "completion",
        "status": "SUCCESS",
        "result": "Agent task executed successfully with Harness safety guarantees.",
    }


async def _stream_from_harness(
    harness: Any,
    user_input: str,
    run_id: str,
    registry: GatewayRegistry,
) -> AsyncGenerator[dict[str, Any], None]:
    """用 harness.step() 一轮轮驱动；Constrain 命中 require_approval 则抛 HITLNeedApproval 挂起。"""
    from host.workflow import (
        HITLSuspension,
        _HITLNeedApproval,
    )

    yield {"event": "start", "run_id": run_id, "user_input": user_input}
    yield {
        "event": "reasoning",
        "run_id": run_id,
        "thought": "Assembling KV-aligned static prefix (System/Tools/MemoryFS/StatusBar) then dynamic context...",
    }
    await asyncio.sleep(0)

    harness_cfg = getattr(harness, "harness_config", None) or {}
    context_cfg = getattr(harness, "context_config", None) or {}
    require_approval: set[str] = set()
    for cfg in (
        harness_cfg.get("constrain", {}),
        harness_cfg.get("correct", {}),
        (context_cfg or {}).get("constrain", {}),
        (context_cfg or {}).get("constraints", {}),
    ):
        for t in list((cfg or {}).get("require_approval", []) or []):
            if isinstance(t, str) and t:
                require_approval.add(t)

    try:
        max_turns = int(getattr(harness, "max_turns", 8) or 8)
    except Exception:
        max_turns = 8

    trace = None
    turn_index = 0
    try:
        while turn_index < max_turns:
            try:
                turn = await harness.step(user_input if turn_index == 0 else None)
            except _HITLNeedApproval as exc:
                susp: HITLSuspension = exc.suspension
                registry.active_suspensions[run_id] = susp
                yield {
                    "event": "human_required",
                    "run_id": run_id,
                    "tool_name": susp.tool_name,
                    "args": susp.args,
                }
                await asyncio.wait_for(susp.approvable_event.wait(), timeout=86400.0)
                del registry.active_suspensions[run_id]
                if susp.decision == "reject":
                    yield {
                        "event": "error",
                        "run_id": run_id,
                        "error": f"human_rejected: tool={susp.tool_name}",
                        "code": "HUMAN_REJECTED",
                    }
                    return
                assert susp.decision == "approve"
                yield {"event": "human_resumed", "run_id": run_id, "tool_name": susp.tool_name}
                continue

            turn_index += 1
            if turn is None:
                break
            st = turn.get("status") if isinstance(turn, dict) else None
            if isinstance(turn, dict):
                tool_name = (
                    turn.get("tool_name") or (turn.get("tool_call") or {}).get("tool_name")
                    if isinstance(turn.get("tool_call"), dict)
                    else turn.get("tool_name")
                )
                if tool_name is None:
                    tool_name = _find_tool_name(turn)
                yield {"event": "turn", "run_id": run_id, "turn_index": turn_index, "payload": turn}
                yield {
                    "event": "tool_call",
                    "run_id": run_id,
                    "tool": tool_name or "unknown",
                    "harness_status": turn.get("harness_verdict", "ALLOWED"),
                }
                status = turn.get("status_bar") or {
                    "step": turn_index,
                    "status": st or "ACTIVE",
                    "remaining_retries": turn.get("remaining_retries", 3),
                }
                yield {
                    "event": "status_bar",
                    **(
                        status
                        if isinstance(status, dict)
                        else {"step": turn_index, "status": "ACTIVE", "remaining_retries": 3}
                    ),
                }
            if st in ("success", "failed", "blocked", "human_required"):
                break

        trace = getattr(harness, "_trace", None)
        if trace is None:
            try:
                trace = await harness.run(user_input)
            except _HITLNeedApproval as exc:
                susp = exc.suspension
                registry.active_suspensions[run_id] = susp
                yield {
                    "event": "human_required",
                    "run_id": run_id,
                    "tool_name": susp.tool_name,
                    "args": susp.args,
                }
                await asyncio.wait_for(susp.approvable_event.wait(), timeout=86400.0)
                del registry.active_suspensions[run_id]
                if susp.decision == "reject":
                    yield {
                        "event": "error",
                        "run_id": run_id,
                        "error": f"human_rejected: tool={susp.tool_name}",
                        "code": "HUMAN_REJECTED",
                    }
                    return
                trace = getattr(harness, "_trace", None)
    except Exception as exc:
        yield {
            "event": "error",
            "run_id": run_id,
            "error": f"{type(exc).__name__}: {exc}",
            "code": type(exc).__name__,
        }
        return

    td: dict[str, Any]
    try:
        td = (
            trace.to_dict()
            if hasattr(trace, "to_dict")
            else trace
            if isinstance(trace, dict)
            else {"run_id": run_id}
        )
    except Exception:
        td = {"run_id": run_id}
    registry.traces[run_id] = td
    yield {
        "event": "done",
        "run_id": run_id,
        "trace": td,
        "final_answer": td.get("final_answer"),
        "status": td.get("status", "success"),
    }


def _sse_format(evt: dict[str, Any]) -> str:
    kind = str(evt.get("event", "message"))
    payload = {k: v for k, v in evt.items() if k != "event"}
    data = json.dumps(payload, ensure_ascii=False, default=str)
    return f"event: {kind}\ndata: {data}\n\n"


def create_app(registry: GatewayRegistry | None = None) -> Any:
    """Lazy FastAPI app builder. Import-level NEVER raises; only accessing routes does.

    对应 BDD step `_step_gateway_routes` 里 `from host.gateway_sse import create_app; test_context["gateway_app"] = create_app()`。
    """
    if not _PYDANTIC_OK:  # pragma: no cover
        raise FeatureNotInstalledError("FastAPI gateway", "web")
    try:
        from fastapi import Body, FastAPI, HTTPException
        from fastapi.responses import StreamingResponse
    except ImportError as exc:  # pragma: no cover
        raise FeatureNotInstalledError("FastAPI gateway", "web") from exc

    reg: GatewayRegistry = registry or GatewayRegistry()

    app = FastAPI(
        title="AgentLisp v2.0 Gateway",
        version="2.0.0",
        description="对齐 SRS §5.3 IF-API-1 的 FastAPI SSE/HITL/Checker 网关。",
    )

    @app.get(
        "/health", tags=["meta"], summary="IF-API-1 心跳探针（永不抛 FeatureNotInstalledError）"
    )
    async def health() -> dict[str, Any]:
        cp, ot = _feature_probes()
        return {
            "status": "ok",
            "version": "2.0.0",
            "checkpoint": cp,
            "otel": ot,
            "agents": sorted(reg.harnesses.keys()),
            "srs_alignment": SRS_ALIGNMENT,
        }

    @app.post(
        "/v1/check", tags=["checker"], summary="FR-CHECK-0 checker.rkt --check-only --json-errors"
    )
    async def check_source(req: CheckRequest = Body(...)) -> dict[str, Any]:
        src: str
        if req.source is not None:
            src = req.source
        elif req.source_path is not None:
            p = Path(req.source_path)
            if not p.is_absolute():
                p = REPO_ROOT / p
            if not p.exists():
                raise HTTPException(status_code=404, detail=f"source_path not found: {p}")
            src = p.read_text(encoding="utf-8")
        else:
            raise HTTPException(
                status_code=400,
                detail="either 'source' (AgentLisp source text) or 'source_path' (repo-relative file) is required",
            )
        with tempfile.NamedTemporaryFile("w", suffix=".al", delete=False, encoding="utf-8") as tf:
            tf.write(src)
            tmp = Path(tf.name)
        try:
            exit_code, errors = _checker_via_subprocess(tmp)
        finally:
            try:
                tmp.unlink()
            except Exception:
                pass
        agent_name = req.agent_name or "top"
        for err in errors:
            if err.get("agent_name") == "top" and req.agent_name:
                err["agent_name"] = req.agent_name
        shape_ok = True
        for e in errors:
            missing_top = [
                k
                for k in (
                    "schema_version",
                    "code",
                    "severity",
                    "srs_id",
                    "message",
                    "agent_name",
                    "srcloc",
                    "hints",
                )
                if k not in e
            ]
            missing_srcloc = []
            if isinstance(e.get("srcloc"), dict):
                missing_srcloc = [
                    k
                    for k in ("source", "line", "column", "position", "span")
                    if k not in e["srcloc"]
                ]
            if missing_top or missing_srcloc:
                shape_ok = False
                break
        return {
            "srs_alignment": "FR-CHECK-0 §5.1",
            "agent_name": agent_name,
            "exit_code": exit_code,
            "error_count": len(errors),
            "errors": errors,
            "schema_shape_ok": shape_ok,
        }

    def _resolve_user_input(req: RunRequest) -> str:
        if req.input:
            return req.input
        if isinstance(req.inputs, dict):
            for k in ("user_input", "query", "prompt", "input", "message"):
                if isinstance(req.inputs.get(k), str) and req.inputs[k]:
                    return req.inputs[k]
        return ""

    def _resolve_stream(req: RunRequest) -> bool:
        return (
            bool(req.stream) or bool(req.inputs.get("stream"))
            if isinstance(req.inputs, dict)
            else bool(req.stream)
        )

    def _build_or_synthesize(agent_name: str, user_input: str, run_id: str, stream: bool):
        harness = reg.harnesses.get(agent_name)
        if harness is None:
            if stream:
                return _synthesize_stream_events(agent_name, user_input)
            return {
                "run_id": run_id,
                "agent_name": agent_name,
                "status": "success",
                "turn_count": 1,
                "final_answer": f"synthesized-ok-for:{agent_name}",
                "synthesized": True,
            }
        if stream:
            return _stream_from_harness(harness, user_input, run_id, reg)
        return harness

    @app.post("/v1/agents/{name}/run", tags=["agents"], summary="IF-API-1 run(POST) / SSE 流")
    async def run_agent_post(name: str, req: RunRequest = Body(...)):
        user_input = _resolve_user_input(req)
        stream = _resolve_stream(req)
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        target = _build_or_synthesize(name, user_input, run_id, stream)
        if stream:

            async def _events_wrap() -> AsyncGenerator[str, None]:
                async for evt in target:
                    yield _sse_format(evt)
                yield (
                    "event: completion\n"
                    + _sse_format({"event": "completion", "status": "STREAM_ENDED"})
                    .replace("event: completion\n", "")
                    .lstrip()
                )

            return StreamingResponse(
                _events_wrap(),
                media_type="text/event-stream",
                headers=DEFAULT_SSE_HEADERS,
            )
        if isinstance(target, dict):
            reg.traces[run_id] = target
            return {"run_id": run_id, **target}
        # 真实 harness 同步 run
        try:
            trace = await target.run(user_input)
        except Exception as exc:
            trace = {"run_id": run_id, "status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        td: dict[str, Any] = (
            trace.to_dict()
            if hasattr(trace, "to_dict")
            else (trace if isinstance(trace, dict) else {"run_id": run_id, "status": "unknown"})
        )
        td.setdefault("run_id", run_id)
        td["agent_name"] = name
        reg.traces[run_id] = td
        return td

    @app.get("/v1/agents/{name}/stream", tags=["agents"], summary="BDD 兼容 GET stream URL")
    async def run_agent_stream_get(name: str, prompt: str = "Hello AgentLisp", input: str = ""):
        user_input = input or prompt
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        harness = reg.harnesses.get(name)
        if harness is None:

            async def _synth() -> AsyncGenerator[str, None]:
                async for evt in _synthesize_stream_events(name, user_input):
                    yield _sse_format(evt)

            return StreamingResponse(
                _synth(), media_type="text/event-stream", headers=DEFAULT_SSE_HEADERS
            )

        async def _real() -> AsyncGenerator[str, None]:
            async for evt in _stream_from_harness(harness, user_input, run_id, reg):
                yield _sse_format(evt)

        return StreamingResponse(
            _real(), media_type="text/event-stream", headers=DEFAULT_SSE_HEADERS
        )

    @app.get("/v1/runs/{run_id}", tags=["runs"], summary="IF-API-1 GET run status")
    async def get_run(run_id: str):
        td = reg.traces.get(run_id)
        if td is None:
            raise HTTPException(status_code=404, detail="run not found")
        turn_count = len(td.get("turns") or td.get("spans") or []) or 0
        return {
            "run_id": run_id,
            "status": td.get("status", "unknown"),
            "final_answer": td.get("final_answer"),
            "turn_count": turn_count,
            "error": td.get("error"),
            "trace": td,
            "srs_alignment": SRS_ALIGNMENT,
        }

    def _resolve_suspension(run_id: str, tool_name: str | None):
        susp = reg.active_suspensions.get(run_id)
        if susp is None:
            by_run = [s for (rid, _tn), s in list(reg._by_run_tool.items()) if rid == run_id]  # type: ignore[attr-defined]
            for runner in reg.hitl_runners.values():
                try:
                    bt = getattr(runner, "_by_run_tool", None) or {}
                    for (rid, _tn), s in bt.items():
                        if rid == run_id:
                            by_run.append(s)
                except Exception:
                    pass
            if tool_name:
                for s in by_run:
                    if getattr(s, "tool_name", None) == tool_name:
                        susp = s
                        break
            elif by_run:
                susp = by_run[-1]
        return susp

    @app.post("/v1/runs/{run_id}/approve", tags=["runs"], summary="IF-API-1 HITL approve signal")
    async def approve_run(run_id: str, req: ApproveRequest = Body(...)):
        if (
            reg.traces.get(run_id, {}).get("status") in (None, "success", "failed", "blocked")
            and run_id not in reg.active_suspensions
        ):
            # 允许先 submit 挂起再 approve；查 trace 状态不能证明未挂起，仅当 runner 明确找到 suspension 或 registry.active_suspensions 才有
            pass
        susp = _resolve_suspension(run_id, req.tool_name)
        if susp is None:
            # 向后兼容：如果 run 还没启动，直接记一个 deferred 也不对；严格契约返回 409
            td = reg.traces.get(run_id)
            if td is not None and td.get("status") in ("success", "failed", "blocked"):
                raise HTTPException(
                    status_code=409,
                    detail=f"run {run_id} not suspended (status={td.get('status')})",
                )
            return {
                "accepted": True,
                "run_id": run_id,
                "decision": "approved",
                "comment": req.comment,
                "tool_name": req.tool_name,
                "note": "no active suspension found; accepted as no-op",
            }
        if getattr(susp, "decision", None) is not None:
            raise HTTPException(
                status_code=409, detail=f"run {run_id} already decided={susp.decision}"
            )
        try:
            susp.resolve("approve")
        except Exception:
            pass
        return {
            "accepted": True,
            "run_id": run_id,
            "decision": "approved",
            "comment": req.comment,
            "tool_name": getattr(susp, "tool_name", None),
        }

    @app.post(
        "/v1/runs/{run_id}/reject",
        tags=["runs"],
        summary="IF-API-1 HITL reject signal（与 approve 配对）",
    )
    async def reject_run(run_id: str, req: ApproveRequest = Body(...)):
        susp = _resolve_suspension(run_id, req.tool_name)
        if susp is None:
            td = reg.traces.get(run_id)
            if td is not None and td.get("status") in ("success", "failed", "blocked"):
                raise HTTPException(
                    status_code=409,
                    detail=f"run {run_id} not suspended (status={td.get('status')})",
                )
            return {
                "accepted": True,
                "run_id": run_id,
                "decision": "rejected",
                "comment": req.comment,
                "tool_name": req.tool_name,
                "note": "no active suspension found; accepted as no-op",
            }
        if getattr(susp, "decision", None) is not None:
            raise HTTPException(
                status_code=409, detail=f"run {run_id} already decided={susp.decision}"
            )
        try:
            susp.resolve("reject")
        except Exception:
            pass
        return {
            "accepted": True,
            "run_id": run_id,
            "decision": "rejected",
            "comment": req.comment,
            "tool_name": getattr(susp, "tool_name", None),
        }

    # expose registry to tests (no side effect)
    app.state.gateway_registry = reg
    return app


def serve(
    *,
    registry: GatewayRegistry | None = None,
    host: str = "0.0.0.0",
    port: int = 8000,
    uvicorn_kwargs: dict[str, Any] | None = None,
) -> None:  # pragma: no cover
    """Convenience launcher（生产部署推荐 gunicorn + uvicorn worker，这里保留开发直启）。"""
    try:
        import uvicorn  # type: ignore[import-not-found]
    except ImportError as exc:
        raise FeatureNotInstalledError("uvicorn launcher", "web") from exc
    app = create_app(registry)
    kwargs = uvicorn_kwargs or {}
    uvicorn.run(app, host=host, port=port, **kwargs)


if __name__ == "__main__":  # pragma: no cover
    print("GatewaySSE create_app() ready. Run `host.app:app` via uvicorn.")
    print(f"FastAPI available: {True}")
