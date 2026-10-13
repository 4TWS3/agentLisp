"""端口与内存 Mock（设计 v2 §7）：批 3 的 topic-model / a2a / learning 依赖外部能力。

硬规则：Mock/Null 适配器**必须显式告警**（不许静默降级）。
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class Retriever(Protocol):
    def search(self, query: str, k: int = 3) -> list[str]: ...


class MessageBus(Protocol):
    def send(self, to_agent: str, payload: dict) -> dict: ...


class SkillStore(Protocol):
    def put(self, key: str, value: Any) -> None: ...
    def get(self, key: str) -> Any: ...


class InMemoryRetriever:
    """测试用检索器：夹具语料 + 记录调用。"""

    adapter = "mock"

    def __init__(self, corpus: list[str] | None = None) -> None:
        self.corpus = list(corpus or [])
        self.calls: list[tuple[str, int]] = []
        logger.warning("Retriever 使用内存 Mock 适配器（adapter=mock）：仅测试用，非生产")

    def search(self, query: str, k: int = 3) -> list[str]:
        self.calls.append((query, k))
        hits = [doc for doc in self.corpus if query.lower() in doc.lower()]
        return (hits or self.corpus)[:k]


class InMemoryBus:
    adapter = "mock"

    def __init__(self) -> None:
        self.sent: list[dict] = []
        logger.warning("MessageBus 使用内存 Mock 适配器（adapter=mock）：仅测试用，非生产")

    def send(self, to_agent: str, payload: dict) -> dict:
        msg = {"to": to_agent, "payload": dict(payload)}
        self.sent.append(msg)
        return {"delivered": True, "to": to_agent, "echo": payload.get("id")}


class InMemorySkillStore:
    adapter = "mock"

    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        logger.warning("SkillStore 使用内存 Mock 适配器（adapter=mock）：仅测试用，非生产")

    def put(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str) -> Any:
        return self.data.get(key)
