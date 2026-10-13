"""M3 测试：模式介入留痕（观测）+ 生产适配器真实落盘/真实检索。"""

from __future__ import annotations

from pathlib import Path

from runtime.base_harness_v2 import BaseHarnessV2
from runtime.patterns.adapters import FileCorpusRetriever, FileSkillStore


def _harness() -> BaseHarnessV2:
    return BaseHarnessV2({"system_prompt": "s"}, {}, {}, {})


def test_intervention_is_recorded() -> None:
    """观测：hitl 拦截必须留痕（events 里能看到 kind/hook/why）。"""
    h = _harness()
    h.PATTERNS = [{"pattern": "hitl", "approval-before": ["deploy"]}]
    from runtime.patterns import load

    load(h)
    ok, _ = h.constrain({"tool_name": "deploy", "args": {}})
    assert ok is False
    ev = h.patterns.events_for("hitl")
    assert ev and ev[-1]["hook"] == "on_tool_call" and ev[-1]["detail"]["blocked"] is True, (
        f"应记录拦截事件；实际 {ev!r}"
    )


def test_file_skill_store_round_trip(tmp_path: Path) -> None:
    """生产适配器：learning 真的落盘（契约 CT-LEARNING-01「落盘 + 下次生效」）。"""
    store = FileSkillStore(tmp_path / "skills")
    h = _harness()
    h.PATTERNS = [{"pattern": "learning", "skill-dir": "skills"}]
    from runtime.patterns import load

    load(h, adapters={"learning": store})
    key = h.patterns.api("learning").write_back({"id": "fb9", "text": "先验后动"})
    assert store.get(key) == {"id": "fb9", "text": "先验后动"}
    files = list((tmp_path / "skills").glob("*.json"))
    assert len(files) == 1, f"应落盘 1 个文件；实际 {files!r}"


def test_file_corpus_retriever_reads_disk(tmp_path: Path) -> None:
    """生产适配器：rag 的检索真的读盘。"""
    (tmp_path / "a.txt").write_text("billing 流程说明", encoding="utf-8")
    (tmp_path / "b.txt").write_text("auth 认证说明", encoding="utf-8")
    r = FileCorpusRetriever(tmp_path)
    assert r.search("billing") == ["a.txt"], "应命中 a.txt"
    assert r.search("nothing") == [], "无命中返回空（并告警）"


def test_m3_counterproof_without_patterns_has_no_events() -> None:
    h = _harness()
    assert h.patterns.events == [], "反证：未声明模式不得产生事件"
