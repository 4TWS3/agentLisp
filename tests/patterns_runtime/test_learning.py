"""契约 CT-LEARNING-01 的运行时测试（行为 1 条 + 反证 1 条）。"""

from __future__ import annotations

from runtime.base_harness_v2 import BaseHarnessV2


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({}, {}, {}, {})


def test_learning_behavior() -> None:
    h = _harness()
    h.PATTERNS = [{"pattern": "learning", "skill-dir": ".agentlisp/skills"}]
    from runtime.patterns import load

    load(h)
    ll = h.patterns.api("learning")
    assert ll.skill_dir() == ".agentlisp/skills"
    k = ll.write_back({"id": "fb1", "text": "慢一步"})
    assert "fb1" in k and ll.recall(k) == {"id": "fb1", "text": "慢一步"}
    assert "pattern:learning" in str(h.build_context()), "CT-LEARNING-01：上下文应含指令"


def test_learning_counterproof() -> None:
    h = _harness()
    assert h.patterns.handlers == []
    assert "pattern:learning" not in str(h.build_context())
