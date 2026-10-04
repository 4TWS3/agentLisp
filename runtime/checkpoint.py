"""Checkpoint store abstraction: in-memory + optional Redis."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

from .errors import CheckpointError, FeatureNotInstalledError


class CheckpointStore(Protocol):
    async def save(self, run_id: str, snapshot: dict[str, Any]) -> None: ...
    async def load(self, run_id: str) -> dict[str, Any] | None: ...


class MemoryCheckpointStore:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def save(self, run_id: str, snapshot: dict[str, Any]) -> None:
        self._store.setdefault(run_id, {}).update(snapshot)

    async def load(self, run_id: str) -> dict[str, Any] | None:
        return self._store.get(run_id)


class RedisCheckpointStore:
    """Redis checkpoint backend. Requires `uv pip install 'agentlisp[durable]'`.

    SRS NFR-REL-1（Appendix B）默认 TTL 固定为 86400s（24h），防止 7×24h 默认值过大导致 Redis 内存 OOM。
    允许调用方覆盖为更长值，但在 containerized 部署下推荐默认值。
    """

    # SRS R4 可测性强制要求：ttl 默认值 ≡ 86400 秒（必须能通过 getattr 断言）
    DEFAULT_TTL_SECONDS: int = 86400

    def __init__(
        self,
        url: str | None = None,
        *,
        key_prefix: str = "agentlisp:ckpt:",
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        client: Any | None = None,
    ) -> None:
        if client is None:
            try:
                from redis.asyncio import Redis  # type: ignore[import-not-found]
            except ImportError as exc:
                raise FeatureNotInstalledError("Redis checkpoint", "durable") from exc
            self._redis = Redis.from_url(
                url or os.getenv("AGENTLISP_REDIS_URL", "redis://localhost:6379/0")
            )
        else:
            self._redis = client
        self.prefix = key_prefix
        if not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
            raise ValueError(f"ttl_seconds must be a positive integer, got {ttl_seconds!r}")
        self.ttl = ttl_seconds

    def _key(self, run_id: str) -> str:
        return f"{self.prefix}{run_id}"

    async def save(self, run_id: str, snapshot: dict[str, Any]) -> None:
        try:
            payload = json.dumps(snapshot, ensure_ascii=False, default=str).encode()
            await self._redis.hsetnx(self._key(run_id), "v", payload)  # type: ignore[union-attr]
            existing = await self._redis.hget(self._key(run_id), "v")  # type: ignore[union-attr]
            merged: dict[str, Any] = json.loads(existing or "{}")
            merged.update(snapshot)
            await self._redis.hset(
                self._key(run_id), "v", json.dumps(merged, default=str, ensure_ascii=False).encode()
            )  # type: ignore[union-attr]
            await self._redis.expire(self._key(run_id), self.ttl)  # type: ignore[union-attr]
        except Exception as exc:
            raise CheckpointError(f"save {run_id} failed: {exc}") from exc

    async def load(self, run_id: str) -> dict[str, Any] | None:
        try:
            raw = await self._redis.hget(self._key(run_id), "v")  # type: ignore[union-attr]
            if not raw:
                return None
            return json.loads(raw)
        except Exception as exc:
            raise CheckpointError(f"load {run_id} failed: {exc}") from exc
