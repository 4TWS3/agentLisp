"""AgentLisp v2 E2B MicroVM sandbox driver (NFR-SEC-1c).

对齐 host/sandbox.py:Sandbox ABC；未装 `agentlisp[sandbox]` + `e2b` SDK 时抛 FeatureNotInstalledError（install_group="sandbox"），形状对齐 DockerSandbox / NullSandbox。

install_group = "sandbox"（与 DockerSandbox 共用 optional-deps 组名；若未来拆分 `e2b` 独立组，保持 install_group 不切换避免下游判断变更）。
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

from runtime.errors import FeatureNotInstalledError

from .sandbox import Sandbox, SandboxRunResult

logger = logging.getLogger("AgentLisp.E2BSandbox")

_DEFAULT_E2B_TEMPLATE = "base"
_E2B_PKG_NOTICE = (
    "E2B SDK 未在当前环境安装。可通过 `uv pip install e2b` 或 "
    "`uv pip install 'agentlisp[sandbox,e2b]'` 后再构造 E2BSandbox。"
)


@dataclass
class E2BSandboxConfig:
    """E2B Sandbox 配置（与 DockerSandbox 命名保持一致，便于上层统一路由）。"""

    api_key: str | None = None
    template: str = _DEFAULT_E2B_TEMPLATE
    timeout: float = 60.0
    memory_limit_mb: int | None = 512
    network_mode: str = "none"

    def effective_api_key(self) -> str | None:
        return self.api_key or os.getenv("E2B_API_KEY") or os.getenv("E2B_API_TOKEN")


class E2BSandbox(Sandbox):
    """E2B 云端 MicroVM Sandbox。对齐 Sandbox ABC（async run → SandboxRunResult）。

    三类行为（SRS NFR-SEC-1c）：
    1) 构造时未装 `e2b` SDK → raise FeatureNotInstalledError("E2B sandbox", "sandbox")
    2) 构造时无 E2B_API_KEY / config.api_key → 抛 RuntimeError（Feature 已装但缺凭证，非 SDK 缺失）
    3) 正常可用 → run() 调用 e2b Sandbox.commands.exec；失败或超时封装为 SandboxRunResult
    """

    def __init__(
        self,
        *,
        config: E2BSandboxConfig | None = None,
        e2b_client: Any | None = None,
    ) -> None:
        self.cfg = config or E2BSandboxConfig()
        if e2b_client is None:
            try:
                from e2b import Sandbox as _E2BRaw  # type: ignore[import-not-found]
            except ImportError as exc:
                raise FeatureNotInstalledError("E2B sandbox", "sandbox", _E2B_PKG_NOTICE) from exc
            self._raw_cls = _E2BRaw
        else:
            self._raw_cls = e2b_client
        api_key = self.cfg.effective_api_key()
        if not api_key:
            raise RuntimeError(
                "E2BSandbox 需要 E2B_API_KEY (环境变量或 E2BSandboxConfig.api_key)；"
                "当前未检测到。缺凭证无法启动 MicroVM。"
            )
        self._api_key = api_key
        self._vm: Any = None

    async def _ensure_vm(self) -> Any:
        if self._vm is not None:
            return self._vm
        loop = asyncio.get_running_loop()

        def _create() -> Any:
            kwargs: dict[str, Any] = {"api_key": self._api_key, "template": self.cfg.template}
            if self.cfg.memory_limit_mb is not None:
                kwargs["metadata"] = {
                    "memory_limit_mb": self.cfg.memory_limit_mb,
                    "network_mode": self.cfg.network_mode,
                }
            return self._raw_cls(**kwargs)

        self._vm = await loop.run_in_executor(None, _create)
        return self._vm

    async def close(self) -> None:  # pragma: no cover - 依赖 e2b SDK
        vm = self._vm
        self._vm = None
        if vm is None:
            return
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, getattr(vm, "close", lambda: None))
        except Exception:
            logger.warning("E2B sandbox close 失败，已忽略，避免外层流程中断")

    async def run(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout: float = 60.0,
        **_: Any,
    ) -> SandboxRunResult:
        if not command:
            raise ValueError("E2BSandbox.run: command 必须非空 list[str]")
        start = time.perf_counter()
        vm = await self._ensure_vm()
        exec_cmd = " ".join(_sh_quote(c) for c in command)
        merged_env = {**os.environ, **(env or {})}

        async def _exec() -> tuple[int, str, str]:
            loop = asyncio.get_running_loop()

            def _sync() -> tuple[int, str, str]:
                cmds = getattr(vm, "commands", None)
                if cmds is None:
                    raise FeatureNotInstalledError(
                        "E2B sandbox", "sandbox", "E2B SDK 版本过低，缺少 Sandbox.commands 属性"
                    )
                res = cmds.exec(exec_cmd, env=merged_env or None, timeout=timeout)
                exit_code = int(getattr(res, "exit_code", 1) or 1)
                stdout = str(getattr(res, "stdout", "") or "")
                stderr = str(getattr(res, "stderr", "") or "")
                return exit_code, stdout, stderr

            return await loop.run_in_executor(None, _sync)

        try:
            exit_code, stdout, stderr = await asyncio.wait_for(_exec(), timeout=timeout)
        except TimeoutError:
            logger.warning("E2BSandbox.run 超时 timeout=%s，终止 VM：%s", timeout, exec_cmd)
            await self.close()
            raise
        except FeatureNotInstalledError:
            raise
        except Exception as exc:
            return SandboxRunResult(
                exit_code=126,
                stdout="",
                stderr=f"E2B Sandbox 异常：{exc.__class__.__name__}: {exc}",
                duration_ms=(time.perf_counter() - start) * 1000.0,
                metadata={
                    "backend": "e2b",
                    "template": self.cfg.template,
                    "error": exc.__class__.__name__,
                },
            )
        return SandboxRunResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=(time.perf_counter() - start) * 1000.0,
            metadata={
                "backend": "e2b",
                "template": self.cfg.template,
                "network_mode": self.cfg.network_mode,
                "memory_limit_mb": self.cfg.memory_limit_mb,
            },
        )


def _sh_quote(tok: str) -> str:
    """Shell 单引号转义（简单版，足够拼接命令字符串）。"""
    return "'" + tok.replace("'", "'\\''") + "'"
