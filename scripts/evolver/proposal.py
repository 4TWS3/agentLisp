"""离线进化：失败轨迹 -> 结构化提案（US-49）。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TARGETS = ("skills", "prompt-patches", "harness-retry", "pattern-macros")


@dataclass(frozen=True)
class MutationProposal:
    proposal_id: str
    target: str
    diff_content: str
    evidence_trace_id: str
    rationale: str = ""
    first_error: dict[str, Any] = field(default_factory=dict)


def analyze_failure_traces(trace_dir: str | Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(Path(trace_dir).glob("*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))
        # blocked 也算失败证据：被护栏拦下同样是「该改的地方」，不收集就丢了最重要的一类。
        if trace.get("status") in ("failed", "blocked"):
            out.append(trace)
    return out


def _target_for(stage: str | None) -> str:
    return {
        "constrain": "skills",
        "loop": "prompt-patches",
        "exception": "harness-retry",
    }.get(str(stage or ""), "skills")


def generate_mutation_proposal(trace: dict[str, Any]) -> MutationProposal:
    run_id = str(trace.get("run_id") or "unknown")
    fe = trace.get("first_error") or {}
    msg = str(fe.get("message") or trace.get("error") or "")
    return MutationProposal(
        proposal_id="patch_" + run_id,
        target=_target_for(fe.get("stage")),
        diff_content="## auto proposal from trace " + run_id + chr(10) + "- first error: " + msg,
        evidence_trace_id=run_id,
        rationale="stage=" + str(fe.get("stage")) + "; code=" + str(fe.get("code")),
        first_error=dict(fe),
    )
