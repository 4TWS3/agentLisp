"""US-21 / US-22 / US-23：learning / topic-model / a2a 的观测留痕。

US-21：学习条目写到产物之外（技能库），产物文件不变。
US-22：主题分布与命中结果进 trace。
US-23：通信握手状态与 msg_id 进 trace。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from runtime.base_harness_v2 import BaseHarnessV2
from runtime.patterns import load
from runtime.patterns.adapters import FileSkillStore


def _harness(**patterns: object) -> BaseHarnessV2:
    h = BaseHarnessV2({}, {}, {}, {})
    h.PATTERNS = [dict(p) for p in patterns.values()]  # type: ignore[list-item]
    return h


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_learning_write_back_is_outside_artifact(tmp_path: Path) -> None:
    """学习条目写到产物之外；产物文件哈希不变。"""
    artifact = tmp_path / "obs.py"
    artifact.write_text("# artifact stand-in\n", encoding="utf-8")
    before = _hash(artifact)

    h = _harness(learning={"pattern": "learning", "skill-dir": "skills"})
    load(h, adapters={"learning": FileSkillStore(tmp_path / "skills")})
    key = h.patterns.api("learning").write_back({"id": "fb1", "text": "先验后动"})

    assert (tmp_path / "skills").is_dir(), "应写到产物之外的技能目录"
    assert _hash(artifact) == before, "产物文件被改动了"
    events = h.patterns.events_for("learning")
    assert any(e["hook"] == "write_back" and e["detail"]["key"] == key for e in events)


def test_topic_model_records_distribution() -> None:
    h = _harness(topic={"pattern": "topic-model", "processor": "cluster"})
    load(h)
    out = h.patterns.api("topic-model").topics(["billing", "auth", "billing"])
    events = [e for e in h.patterns.events_for("topic-model") if e["hook"] == "topics"]
    assert events, "主题分布没有留痕"
    detail = events[-1]["detail"]
    assert detail["distribution"] == {t: len(v) for t, v in out.items()}
    assert sum(detail["distribution"].values()) == 3


def test_a2a_records_handshake_and_msg_id() -> None:
    h = _harness(a2a={"pattern": "a2a", "protocol": "inmemory"})
    load(h)
    h.patterns.api("a2a").send("worker-1", {"card": "c1", "id": "m1"})
    events = [e for e in h.patterns.events_for("a2a") if e["hook"] == "send"]
    assert events, "通信日志没有留痕"
    detail = events[-1]["detail"]
    assert detail["handshake"] == "ok"
    assert detail["msg_id"] == "m1"
