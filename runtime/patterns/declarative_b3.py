"""批 3：3 个 Mock 端口驱动的 handler（topic-model / a2a / learning）。

端口见 runtime/patterns/ports.py（设计 v2 §7）：测试用内存 Mock，构造时**显式告警** adapter=mock。
键取自编译期注册表：topic-model:processor  a2a:protocol  learning:skill-dir
"""

from __future__ import annotations

import zlib
from typing import Any

from runtime.patterns.ports import InMemoryBus, InMemoryRetriever, InMemorySkillStore


class _B3:
    kind = ""

    def __init__(self, spec: dict) -> None:
        self.spec = spec

    def on_init(self, harness: Any, others: list[str]) -> None:
        self.validate()

    def validate(self) -> None:
        return None

    def before_turn(self, harness: Any, ctx: dict) -> dict:
        msgs = ctx.setdefault("messages", [])
        marker = f"pattern:{self.kind}"
        if not any(isinstance(m, dict) and marker in str(m.get("content", "")) for m in msgs):
            msgs.insert(0, {"role": "system", "content": f"[{marker}] {self.summary()}"})
        return ctx

    def on_tool_call(self, harness: Any, call: dict) -> tuple[bool, str]:
        return True, ""

    def after_turn(self, harness: Any, ctx: dict) -> dict:
        return ctx

    def summary(self) -> str:
        return ""


class TopicModelHandler(_B3):
    kind = "topic-model"

    def __init__(self, spec: dict) -> None:
        super().__init__(spec)
        self.retriever = InMemoryRetriever(corpus=["topic: billing", "topic: auth"])

    def validate(self) -> None:
        if not self.spec.get("processor"):
            raise ValueError("topic-model 需要 :processor（契约 CT-TOPIC_MODEL-01）")

    def summary(self) -> str:
        return f"processor={self.processor()}；主题聚类（检索走 Mock 端口）"

    def processor(self) -> str:
        return str(self.spec["processor"])

    def retrieve(self, query: str, k: int = 3) -> list[str]:
        return self.retriever.search(query, k)

    def topics(self, items: list[str], buckets: int = 2) -> dict[str, list[str]]:
        """确定性分桶（crc32，跨进程稳定；不用 hash() 以免受 PYTHONHASHSEED 影响）。"""
        if buckets <= 0:
            raise ValueError("topic-model：buckets 必须为正")
        out: dict[str, list[str]] = {f"T{i}": [] for i in range(buckets)}
        for it in items:
            out[f"T{zlib.crc32(it.encode('utf-8')) % buckets}"].append(it)
        return out


class A2aHandler(_B3):
    kind = "a2a"

    def __init__(self, spec: dict) -> None:
        super().__init__(spec)
        self.bus = InMemoryBus()

    def validate(self) -> None:
        p = str(self.spec.get("protocol") or "")
        if p not in ("http", "grpc", "inmemory"):
            raise ValueError("a2a 需要 :protocol ∈ {http, grpc, inmemory}（契约 CT-A2A-01）")

    def summary(self) -> str:
        return f"protocol={self.protocol()}；消息必须携带 Agent Card 标识"

    def protocol(self) -> str:
        return str(self.spec["protocol"])

    def send(self, to_agent: str, payload: dict) -> dict:
        if "card" not in payload:
            raise ValueError("a2a：payload 必须含 card（Agent Card 标识，契约 CT-A2A-01）")
        return self.bus.send(to_agent, payload)


class LearningHandler(_B3):
    kind = "learning"

    def __init__(self, spec: dict) -> None:
        super().__init__(spec)
        self.store = InMemorySkillStore()

    def validate(self) -> None:
        if not self.spec.get("skill-dir"):
            raise ValueError("learning 需要 :skill-dir（契约 CT-LEARNING-01）")

    def summary(self) -> str:
        return f"skill-dir={self.skill_dir()}；反馈写回技能层"

    def skill_dir(self) -> str:
        return str(self.spec["skill-dir"])

    def write_back(self, feedback: dict) -> str:
        key = f"{self.skill_dir()}::{feedback.get('id', 'unknown')}"
        self.store.put(key, feedback)
        return key

    def recall(self, key: str) -> Any:
        return self.store.get(key)


B3_HANDLERS: dict[str, type] = {
    "topic-model": TopicModelHandler,
    "a2a": A2aHandler,
    "learning": LearningHandler,
}
