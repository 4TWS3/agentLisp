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
    # 补丁落盘的相对路径（相对 agent 项目根）。空 = 用 target 的默认路径。
    # 为什么要有：pattern-macros 这类目标必须落在 agent 自己的目录，
    # 不能落进共享编译器（否则一个 agent 的进化会改掉所有 agent 的行为）。
    target_path: str = ""


def analyze_failure_traces(trace_dir: str | Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(Path(trace_dir).glob("*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))
        # blocked 也算失败证据：被护栏拦下同样是「该改的地方」，不收集就丢了最重要的一类。
        if trace.get("status") in ("failed", "blocked"):
            out.append(trace)
    return out


def generate_mutation_proposal_with_llm(
    trace: dict[str, Any],
    *,
    model: str = "deepseek-v4-flash",
    api_key: str | None = None,
    base_url: str = "https://api.deepseek.com/v1",
) -> MutationProposal:
    """用模型生成补丁内容；失败退回模板（并在 rationale 里写明退回了）。

    为什么要模型：模板只把 first_error 拼成一句话，那是**提案的形状**，不是提案。
    真提案必须说清「下次遇到同类情况该怎么做」。
    """
    import asyncio
    import os

    from runtime.llm_client import OpenAIClient

    base = generate_mutation_proposal(trace)
    key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
    if not key:
        return MutationProposal(
            **{**base.__dict__, "rationale": base.rationale + "; fallback=no-key"}
        )

    fe = trace.get("first_error") or {}
    prompt = (
        "你在为一个 Agent 设计「技能补丁」。下面是它的失败轨迹摘要。\n"
        f"run_id: {trace.get('run_id')}\n"
        f"status: {trace.get('status')}\n"
        f"first_error: {fe.get('code')} / {fe.get('stage')} / {fe.get('message')}\n"
        f"轮数: {trace.get('turns')}\n"
        "请输出一段 markdown 技能说明（<= 8 行），指导它下次避免同样的失败。\n"
        '只输出 JSON：{"diff_content": "<markdown>"}'
    )
    try:
        llm = OpenAIClient(model=model, api_key=key, base_url=base_url)
        out = asyncio.run(llm.achat([{"role": "user", "content": prompt}]))
        text = str(out.get("content") or "")
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start : end + 1]) if start >= 0 and end > start else {}
        diff = str(data.get("diff_content") or "").strip()
        if not diff:
            raise ValueError("模型没给出 diff_content")
        return MutationProposal(
            proposal_id=base.proposal_id,
            target=base.target,
            diff_content=diff,
            evidence_trace_id=base.evidence_trace_id,
            rationale=base.rationale + "; generated=llm",
            first_error=base.first_error,
        )
    except Exception as exc:
        return MutationProposal(
            **{**base.__dict__, "rationale": base.rationale + f"; fallback=llm-error:{exc}"}
        )


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
