"""AgentLisp v2 BaseHarness ReAct loop & pipeline skeleton."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterable, Callable, Optional

import structlog
from pydantic import BaseModel, Field

from .errors import HarnessError, ToolNotFoundError

log = structlog.get_logger()


@dataclass
class ReActTurn:
    index: int
    thought: str = ""
    action_name: str = ""
    action_input: dict[str, Any] = field(default_factory=dict)
    observation: Any = None
    answer: str = ""
    started_at: float = field(default_factory=time.perf_counter)
    finished_at: Optional[float] = None

    def finish(self) -> None:
        self.finished_at = time.perf_counter()

    @property
    def duration_ms(self) -> float:
        end = self.finished_at if self.finished_at is not None else time.perf_counter()
        return (end - self.started_at) * 1000.0


class ExecutionTrace(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    turns: list[dict[str, Any]] = Field(default_factory=list)
    final_answer: str = ""
    status: str = "pending"
    started_at: float = Field(default_factory=time.perf_counter)
    finished_at: Optional[float] = None
    error: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        end = self.finished_at if self.finished_at is not None else time.perf_counter()
        return (end - self.started_at) * 1000.0


class BaseHarness:
    """ReAct 循环 + Harness 管道基类。

    设计目标：
      1. 完全无外部依赖也能跑（通过 MockLLM / NullTool / MemoryCheckpoint）；
      2. Compiler 输出直接继承此类；
      3. 支持 run / run_async / stream_async 三种调用方式；
      4. 每次调用生成一条 ExecutionTrace（证据链）。
    """

    agent_name: str = ""

    def __init__(
        self,
        agent_cfg: Optional[dict[str, Any]] = None,
        llm_client: Optional[Any] = None,
        tool_registry: Optional[Any] = None,
        checkpoint_store: Optional[Any] = None,
        memory_fs: Optional[Any] = None,
        status_bar: Optional[Any] = None,
        max_turns: int = 30,
        react_mode: bool = True,
    ) -> None:
        self.cfg = agent_cfg or {}
        self.agent_name = self.agent_name or str(self.cfg.get("name", "unnamed-agent"))
        self.llm = llm_client or _NullLLM()
        self.tools = tool_registry or _NullToolRegistry()
        self.checkpoint = checkpoint_store or _MemoryCheckpoint()
        self.memory = memory_fs or _NullMemoryFS()
        self.status_bar = status_bar or _NullStatusBar()
        self.max_turns = int(max_turns)
        self.react_mode = bool(react_mode)
        self._hooks: dict[str, list[Callable[..., Any]]] = {}

    # ------------------------------------------------------------------ hooks
    def on(self, event: str, cb: Callable[..., Any]) -> None:
        self._hooks.setdefault(event, []).append(cb)

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        for cb in self._hooks.get(event, []):
            try:
                cb(payload)
            except Exception:  # noqa: BLE001
                log.exception("hook.failed", event=event)

    # ------------------------------------------------------------- public API
    def run(self, inputs: Optional[dict[str, Any]] = None, **kwargs: Any) -> ExecutionTrace:
        return asyncio.run(self.run_async(inputs=inputs, **kwargs))

    async def run_async(
        self,
        inputs: Optional[dict[str, Any]] = None,
        workflow: Optional[str] = None,
    ) -> ExecutionTrace:
        trace = ExecutionTrace(agent_name=self.agent_name)
        try:
            await self.status_bar.on_start(trace, inputs or {})
            self._emit("start", {"run_id": trace.run_id, "inputs": inputs})
            await self.checkpoint.save(trace.run_id, {"stage": "start", "inputs": inputs})

            if workflow and (engine := self._legacy_engine()):
                from agentlisp_runtime.models import ExecutionContext  # noqa: F401

                result = await engine.run_workflow(
                    workflow_name=workflow,
                )
                for step in result.steps:
                    t = ReActTurn(
                        index=len(trace.turns),
                        action_name=f"step:{step.step_id}",
                        action_input={"status": step.status.value},
                        observation=step.output,
                    )
                    t.finish()
                    trace.turns.append(_turn_to_dict(t))
                trace.final_answer = _jsonable_snapshot(result)
                trace.status = result.status.value
            else:
                await self._react_loop(trace, inputs or {})

            trace.status = "success" if trace.status == "pending" else trace.status
            self._emit("done", {"run_id": trace.run_id, "answer": trace.final_answer})
            await self.status_bar.on_done(trace)
        except Exception as exc:  # noqa: BLE001
            trace.status = "failed"
            trace.error = str(exc)
            log.exception("harness.failed", run_id=trace.run_id, error=str(exc))
            await self.status_bar.on_error(trace, exc)
            self._emit("error", {"run_id": trace.run_id, "error": str(exc)})
            raise HarnessError(f"run {trace.run_id} failed: {exc}") from exc
        finally:
            trace.finished_at = time.perf_counter()
            await self.checkpoint.save(trace.run_id, {"trace": trace.model_dump(mode="json")})
        return trace

    async def stream_async(
        self, inputs: Optional[dict[str, Any]] = None, **_kw: Any
    ) -> AsyncIterable[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        def _enqueue(payload: dict[str, Any]) -> None:
            q.put_nowait(payload)

        self.on("start", lambda p: _enqueue({"event": "start", **p}))
        self.on("turn", lambda p: _enqueue({"event": "turn", **p}))
        self.on("done", lambda p: _enqueue({"event": "done", **p}))
        self.on("error", lambda p: _enqueue({"event": "error", **p}))

        task = asyncio.create_task(self.run_async(inputs=inputs))

        while not task.done() or not q.empty():
            try:
                item = await asyncio.wait_for(q.get(), timeout=0.1)
                yield item
            except TimeoutError:
                continue
        # drain remaining
        while not q.empty():
            yield q.get_nowait()
        await task

    # ------------------------------------------------------------- ReAct core
    async def _react_loop(self, trace: ExecutionTrace, inputs: dict[str, Any]) -> None:
        prompt_payload = {
            "agent": self.agent_name,
            "purpose": self.cfg.get("purpose", ""),
            "tools": self.cfg.get("tools", []),
            "workflows": self.cfg.get("workflows", []),
            "inputs": inputs,
        }
        history: list[dict[str, Any]] = []

        for idx in range(self.max_turns):
            turn = ReActTurn(index=idx)
            self._emit("turn", {"index": idx, "stage": "think"})
            try:
                response = await self.llm.next(prompt_payload, history, trace)
            except Exception as exc:  # noqa: BLE001
                raise HarnessError(f"LLM call failed at turn {idx}: {exc}") from exc

            structured = self._coerce_llm_response(response)
            turn.thought = structured.get("thought", "")
            turn.action_name = structured.get("action", "")
            turn.action_input = structured.get("action_input", {}) or {}

            if structured.get("answer") or structured.get("final_answer"):
                turn.answer = structured.get("answer") or structured.get("final_answer", "")
                trace.final_answer = turn.answer
                turn.finish()
                trace.turns.append(_turn_to_dict(turn))
                self._emit("turn", {"index": idx, "stage": "answer", "answer": turn.answer})
                return

            try:
                obs = await self._dispatch_tool(turn.action_name, turn.action_input)
            except ToolNotFoundError:
                obs = {"error": f"tool not found: {turn.action_name}"}
            turn.observation = obs
            turn.finish()
            history.append({"role": "assistant", **_turn_to_dict(turn)})
            history.append({"role": "observation", "index": idx, "value": _jsonable_snapshot(obs)})
            trace.turns.append(_turn_to_dict(turn))
            await self.checkpoint.save(trace.run_id, {"turns": trace.turns})
            await self.status_bar.on_step(trace, turn)
            self._emit("turn", {"index": idx, "stage": "observed", "observation": obs})

        raise HarnessError(f"ReAct exceeded max_turns={self.max_turns}")

    @staticmethod
    def _coerce_llm_response(raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            return {"thought": raw[:500]}
        if hasattr(raw, "model_dump"):
            return dict(raw.model_dump())  # type: ignore[attr-defined]
        return {"thought": str(raw)[:500]}

    async def _dispatch_tool(self, action_name: str, action_input: dict[str, Any]) -> Any:
        if not action_name:
            return {"skipped": True}
        if hasattr(self.tools, "call"):
            return await self.tools.call(action_name, **action_input)
        if hasattr(self.tools, "get"):
            fn = self.tools.get(action_name)
            if callable(fn):
                if asyncio.iscoroutinefunction(fn):
                    return await fn(**action_input)
                return fn(**action_input)
        raise ToolNotFoundError(f"no handler for action: {action_name}")

    # ----------------------------------------------------------- v0.1 bridge
    def _legacy_engine(self) -> Any | None:
        try:
            from agentlisp_runtime.loader import AgentLoader
            from agentlisp_runtime.engine import AgentEngine
        except Exception:  # noqa: BLE001
            return None
        try:
            agent = AgentLoader.from_dict(self.cfg)
            handlers = {
                k: v for k, v in (self.tools.handlers() if hasattr(self.tools, "handlers") else {})
            }
            return AgentEngine(agent, tool_handlers=handlers)
        except Exception:  # noqa: BLE001
            return None


def _turn_to_dict(t: ReActTurn) -> dict[str, Any]:
    return {
        "index": t.index,
        "thought": t.thought,
        "action": t.action_name,
        "action_input": t.action_input,
        "observation": _jsonable_snapshot(t.observation),
        "answer": t.answer,
        "duration_ms": round(t.duration_ms, 3),
    }


def _jsonable_snapshot(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_jsonable_snapshot(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _jsonable_snapshot(val) for k, val in v.items()}
    if hasattr(v, "model_dump"):
        try:
            return v.model_dump(mode="json")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            return str(v)
    return str(v)


# ----------------------------------------------------------------- null impls
class _NullLLM:
    async def next(
        self, prompt: dict[str, Any], history: list[dict[str, Any]], trace: ExecutionTrace
    ) -> dict[str, Any]:
        # 无 LLM 时默认：最多 1 个 answer 回合，终止
        if any(t.get("answer") for t in trace.turns):
            return {"answer": "<done>"}
        return {
            "thought": "MockLLM: no-op (install llm optional group for real LLM)",
            "action": "",
            "action_input": {},
            "answer": f"finished (mock). inputs={prompt.get('inputs')}",
        }


class _NullToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        self._handlers[name] = fn

    def handlers(self) -> dict[str, Callable[..., Any]]:
        return dict(self._handlers)

    def get(self, name: str) -> Callable[..., Any] | None:
        return self._handlers.get(name)

    async def call(self, name: str, **kwargs: Any) -> Any:
        fn = self._handlers.get(name)
        if fn is None:
            raise ToolNotFoundError(name)
        if asyncio.iscoroutinefunction(fn):
            return await fn(**kwargs)
        return fn(**kwargs)


class _MemoryCheckpoint:
    def __init__(self) -> None:
        self.store: dict[str, dict[str, Any]] = {}

    async def save(self, run_id: str, snapshot: dict[str, Any]) -> None:
        self.store.setdefault(run_id, {}).update(snapshot)

    async def load(self, run_id: str) -> Optional[dict[str, Any]]:
        return self.store.get(run_id)


class _NullMemoryFS:
    async def read(self, path: str) -> Optional[str]:
        return None

    async def write(self, path: str, content: str) -> None:
        return None


class _NullStatusBar:
    async def on_start(self, trace: ExecutionTrace, inputs: dict[str, Any]) -> None:
        log.debug("status.on_start", run_id=trace.run_id)

    async def on_step(self, trace: ExecutionTrace, turn: ReActTurn) -> None:
        log.debug("status.on_step", run_id=trace.run_id, turn=turn.index)

    async def on_done(self, trace: ExecutionTrace) -> None:
        log.debug("status.on_done", run_id=trace.run_id, status=trace.status)

    async def on_error(self, trace: ExecutionTrace, exc: BaseException) -> None:
        log.debug("status.on_error", run_id=trace.run_id, error=str(exc))
