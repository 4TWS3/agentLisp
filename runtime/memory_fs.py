"""Markdown FS (L0/L1/L2) abstraction for DCAF-aligned knowledge storage."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, AsyncIterable, Optional, Protocol

L0_ATOMIC = "atomic"
L1_CONCEPT = "concept"
L2_RULE = "rule"
LAYERS = (L0_ATOMIC, L1_CONCEPT, L2_RULE)


class MemoryFSBackend(Protocol):
    async def read(self, rel_path: str) -> Optional[str]: ...
    async def write(self, rel_path: str, content: str) -> None: ...
    async def list(self, rel_dir: str = "") -> list[str]: ...


class LocalFSBackend:
    def __init__(self, root: os.PathLike[str] | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _full(self, rel: str) -> Path:
        rel = rel.removeprefix("/").removeprefix("\\")
        return self.root / rel

    async def read(self, rel_path: str) -> Optional[str]:
        f = self._full(rel_path)
        if not f.is_file():
            return None
        return f.read_text(encoding="utf-8")

    async def write(self, rel_path: str, content: str) -> None:
        f = self._full(rel_path)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")

    async def list(self, rel_dir: str = "") -> list[str]:
        d = self._full(rel_dir)
        if not d.is_dir():
            return []
        return sorted(p.relative_to(self.root).as_posix() for p in d.rglob("*") if p.is_file())


class MemoryBackend:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def read(self, rel_path: str) -> Optional[str]:
        return self.store.get(rel_path)

    async def write(self, rel_path: str, content: str) -> None:
        self.store[rel_path] = content

    async def list(self, rel_dir: str = "") -> list[str]:
        prefix = rel_dir.rstrip("/") + "/" if rel_dir else ""
        return sorted(k for k in self.store.keys() if not prefix or k.startswith(prefix))


class MemoryFS:
    def __init__(self, backend: Optional[MemoryFSBackend] = None, namespace: str = "default") -> None:
        self.backend: MemoryFSBackend = backend or MemoryBackend()
        self.ns = namespace

    def _layer_path(self, layer: str, key: str) -> str:
        if layer not in LAYERS:
            raise ValueError(f"Invalid layer '{layer}', expected one of {LAYERS}")
        return f"{self.ns}/{layer}/{key.lstrip('/')}"

    async def put(self, layer: str, key: str, content: str) -> None:
        await self.backend.write(self._layer_path(layer, key), content)

    async def get(self, layer: str, key: str) -> Optional[str]:
        return await self.backend.read(self._layer_path(layer, key))

    async def list_layer(self, layer: str) -> list[str]:
        prefix = f"{self.ns}/{layer}/"
        paths = await self.backend.list(f"{self.ns}/{layer}")
        return [p[len(prefix):] for p in paths if p.startswith(prefix)]

    async def iter_all(self) -> AsyncIterable[tuple[str, str, str]]:
        for layer in LAYERS:
            for k in await self.list_layer(layer):
                val = await self.get(layer, k)
                if val is not None:
                    yield layer, k, val
