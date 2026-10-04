"""Sandbox abstraction: NullSandbox (default) + DockerSandbox (optional dep)."""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from runtime.errors import FeatureNotInstalledError


@dataclass
class SandboxRunResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    metadata: dict[str, Any]


class Sandbox(ABC):
    @abstractmethod
    async def run(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> SandboxRunResult: ...


class NullSandbox(Sandbox):
    """No-op sandbox. Executes on the host subprocess directly (NOT isolated).

    Acceptable for local trusted workloads; swap to DockerSandbox in production.
    """

    async def run(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout: float = 60.0,
        **_: Any,
    ) -> SandboxRunResult:
        import time

        start = time.perf_counter()
        merged_env = {**os.environ, **(env or {})}
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=merged_env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            exit_code = int(proc.returncode or 0)
        except TimeoutError as exc:
            proc.kill()
            raise TimeoutError(f"command timed out after {timeout}s") from exc
        return SandboxRunResult(
            exit_code=exit_code,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            duration_ms=(time.perf_counter() - start) * 1000.0,
            metadata={"backend": "null"},
        )


class DockerSandbox(Sandbox):
    """Docker-based sandbox. Requires `uv pip install 'agentlisp[sandbox]'`."""

    def __init__(
        self,
        *,
        image: str = "python:3.12-slim-bookworm",
        docker_client: Any | None = None,
        network_mode: str = "none",
        memory_limit: str | None = "512m",
        read_only: bool = True,
    ) -> None:
        if docker_client is None:
            try:
                import docker  # type: ignore[import-not-found]
            except ImportError as exc:
                raise FeatureNotInstalledError("Docker sandbox", "sandbox") from exc
            self._client = docker.from_env()
        else:
            self._client = docker_client
        self.image = image
        self.network_mode = network_mode
        self.memory = memory_limit
        self.read_only = read_only

    async def run(  # pragma: no cover - docker not reliable in CI
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> SandboxRunResult:
        import time

        start = time.perf_counter()
        loop = asyncio.get_running_loop()

        def _sync() -> tuple[int, str, str]:
            container = self._client.containers.run(
                image=self.image,
                command=command,
                detach=True,
                network_mode=self.network_mode,
                mem_limit=self.memory,
                read_only=self.read_only,
                environment=env or {},
                **kwargs,
            )
            try:
                status = container.wait(timeout=timeout)
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
                return int(status.get("StatusCode", 1)), stdout, stderr
            finally:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

        exit_code, stdout, stderr = await asyncio.wait_for(
            loop.run_in_executor(None, _sync), timeout=timeout
        )
        return SandboxRunResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=(time.perf_counter() - start) * 1000.0,
            metadata={"backend": "docker", "image": self.image},
        )
