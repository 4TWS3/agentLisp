"""US-49：失败轨迹 -> 结构化提案。"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.evolver.proposal import analyze_failure_traces, generate_mutation_proposal


def _write(dir: Path, name: str, payload: dict) -> None:
    (dir / name).write_text(json.dumps(payload), encoding="utf-8")


def test_failed_trace_becomes_structured_proposal(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "r1.json",
        {
            "run_id": "r1",
            "status": "failed",
            "first_error": {"code": "FAILED", "stage": "loop", "message": "boom"},
        },
    )
    failures = analyze_failure_traces(tmp_path)
    assert len(failures) == 1
    p = generate_mutation_proposal(failures[0])
    assert p.evidence_trace_id == "r1"
    assert p.proposal_id == "patch_r1"
    assert p.target == "prompt-patches"
    assert "boom" in p.diff_content
    assert p.first_error["code"] == "FAILED"
    assert p.target in ("skills", "prompt-patches", "harness-retry", "pattern-macros")


def test_successful_trace_is_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "ok.json", {"run_id": "ok", "status": "success"})
    assert analyze_failure_traces(tmp_path) == []


def test_target_maps_constrain_to_skills(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "r2.json",
        {"run_id": "r2", "status": "failed", "first_error": {"stage": "constrain"}},
    )
    p = generate_mutation_proposal(analyze_failure_traces(tmp_path)[0])
    assert p.target == "skills"
