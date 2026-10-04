"""FastAPI HTTP + SSE gateway skeleton.

Imports even without optional web deps installed (raises FeatureNotInstalledError only
when constructing the app; import-level smoke stays green).
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncIterable, Optional

from runtime.errors import FeatureNotInstalledError
from runtime.base_harness import BaseHarness, ExecutionTrace


class Gateway:
    """Lazy FastAPI container. Builds the app only when `app` is accessed; imports fail
    only if optional dep group `web` is missing and user actually instantiates it."""

    def __init__(
        self,
        harness_registry: Optional[dict[str, BaseHarness]] = None,
    ) -> None:
        self.registry: dict[str, BaseHarness] = harness_registry or {}
        self.traces: dict[str, ExecutionTrace] = {}
        self._app: Optional[Any] = None

    def register(self, name: str, harness: BaseHarness) -> None:
        self.registry[name] = harness

    # --------------------------------------------------------- FastAPI lazy build
    @property
    def app(self) -> Any:
        if self._app is None:
            try:
                from fastapi import FastAPI, HTTPException
                from fastapi.responses import StreamingResponse
                from pydantic import BaseModel as _BM
            except ImportError as exc:  # pragma: no cover
                raise FeatureNotInstalledError("FastAPI gateway", "web") from exc

            app = FastAPI(
                title="AgentLisp Gateway",
                version="2.0.0a1",
                description="HTTP/SSE gateway for AgentLisp v2 compiled harnesses",
            )

            class RunRequest(_BM):
                inputs: dict[str, Any] = {}
                workflow: Optional[str] = None
                stream: bool = False

            @app.get("/health", tags=["meta"])
            async def health() -> dict[str, Any]:
                return {
                    "status": "ok",
                    "agents": sorted(self.registry.keys()),
                }

            @app.post("/v1/agents/{name}/run", tags=["agents"])
            async def run_agent(name: str, req: RunRequest):
                if name not in self.registry:
                    raise HTTPException(status_code=404, detail=f"agent not found: {name}")
                if req.stream:
                    trace_ref: dict[str, Any] = {}

                    async def _events() -> AsyncIterable[str]:
                        harness = self.registry[name]
                        async for evt in harness.stream_async(inputs=req.inputs):
                            yield "data: " + json.dumps(evt, default=str, ensure_ascii=False) + "\n\n"
                        final = trace_ref.get("trace")
                        if final is not None:
                            yield "data: " + json.dumps(
                                {"event": "trace", "value": final.model_dump(mode="json")},
                                ensure_ascii=False,
                                default=str,
                            ) + "\n\n"
                        yield "data: [DONE]\n\n"

                    return StreamingResponse(_events(), media_type="text/event-stream")

                trace = await self.registry[name].run_async(
                    inputs=req.inputs, workflow=req.workflow
                )
                self.traces[trace.run_id] = trace
                return trace.model_dump(mode="json")

            @app.get("/v1/runs/{run_id}", tags=["runs"])
            async def get_run(run_id: str):
                t = self.traces.get(run_id)
                if t is None:
                    raise HTTPException(status_code=404, detail="run not found")
                return t.model_dump(mode="json")

            self._app = app
        return self._app


# ---------------------------------------------------------------- quick launcher
def serve(
    gateway: Gateway,
    *,
    host: str = "0.0.0.0",
    port: int = 8000,
    uvicorn_kwargs: Optional[dict[str, Any]] = None,
) -> None:  # pragma: no cover
    """Convenience launcher. Requires 'web' optional group."""
    try:
        import uvicorn  # type: ignore[import-not-found]
    except ImportError as exc:
        raise FeatureNotInstalledError("uvicorn launcher", "web") from exc
    kwargs = uvicorn_kwargs or {}
    uvicorn.run(gateway.app, host=host, port=port, **kwargs)


if __name__ == "__main__":  # pragma: no cover
    from runtime.base_harness import BaseHarness

    gw = Gateway()
    gw.register("demo", BaseHarness(agent_cfg={"name": "demo", "purpose": "smoke"}))
    serve(gw)
