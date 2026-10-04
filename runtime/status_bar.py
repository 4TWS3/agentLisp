"""Context-tail StatusBar Hook (尾部 Hook 协议)."""

from __future__ import annotations

from typing import Any, Protocol

import structlog

from .base_harness import ExecutionTrace, ReActTurn

log = structlog.get_logger()


class StatusBar(Protocol):
    async def on_start(self, trace: ExecutionTrace, inputs: dict[str, Any]) -> None: ...
    async def on_step(self, trace: ExecutionTrace, turn: ReActTurn) -> None: ...
    async def on_done(self, trace: ExecutionTrace) -> None: ...
    async def on_error(self, trace: ExecutionTrace, exc: BaseException) -> None: ...


class PrintingStatusBar:
    async def on_start(self, trace: ExecutionTrace, inputs: dict[str, Any]) -> None:
        print(f"▶ [run_id={trace.run_id}] start agent={trace.agent_name} inputs={list(inputs.keys())}")

    async def on_step(self, trace: ExecutionTrace, turn: ReActTurn) -> None:
        print(
            f"   · turn={turn.index} action={turn.action_name!r} "
            f"duration_ms={turn.duration_ms:.1f}"
        )

    async def on_done(self, trace: ExecutionTrace) -> None:
        ans = trace.final_answer
        if ans and len(ans) > 140:
            ans = ans[:140] + "…"
        print(f"⏹ [run_id={trace.run_id}] status={trace.status} answer={ans!r}")

    async def on_error(self, trace: ExecutionTrace, exc: BaseException) -> None:
        print(f"✘ [run_id={trace.run_id}] error={exc}", flush=True)


class LoggingStatusBar:
    async def on_start(self, trace: ExecutionTrace, inputs: dict[str, Any]) -> None:
        log.info("trace.start", run_id=trace.run_id, agent=trace.agent_name, inputs=sorted(inputs))

    async def on_step(self, trace: ExecutionTrace, turn: ReActTurn) -> None:
        log.debug(
            "trace.step",
            run_id=trace.run_id,
            turn=turn.index,
            action=turn.action_name,
            duration_ms=round(turn.duration_ms, 3),
        )

    async def on_done(self, trace: ExecutionTrace) -> None:
        log.info(
            "trace.done",
            run_id=trace.run_id,
            status=trace.status,
            duration_ms=round(trace.duration_ms, 3),
            turns=len(trace.turns),
        )

    async def on_error(self, trace: ExecutionTrace, exc: BaseException) -> None:
        log.error("trace.error", run_id=trace.run_id, error=str(exc))


class CompositeStatusBar:
    def __init__(self, *bars: StatusBar) -> None:
        self.bars: tuple[StatusBar, ...] = tuple(bars)

    async def on_start(self, trace: ExecutionTrace, inputs: dict[str, Any]) -> None:
        for b in self.bars:
            await b.on_start(trace, inputs)

    async def on_step(self, trace: ExecutionTrace, turn: ReActTurn) -> None:
        for b in self.bars:
            await b.on_step(trace, turn)

    async def on_done(self, trace: ExecutionTrace) -> None:
        for b in self.bars:
            await b.on_done(trace)

    async def on_error(self, trace: ExecutionTrace, exc: BaseException) -> None:
        for b in self.bars:
            await b.on_error(trace, exc)
