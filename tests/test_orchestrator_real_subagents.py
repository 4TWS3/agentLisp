"""US-19 批 2/3（真执行）：spawn / fanout 必须真拉起子 Agent，不是只记决策。

判据：
  - router 的 spawn 真跑一个子 Agent，trace 里有 children_done + worker 名 + 子答案
  - parallel 的 fanout 真并发跑多个，结果条数 == 分支数
"""

from __future__ import annotations

import asyncio
from typing import Any

from runtime.base_harness_v2 import BaseHarnessV2
from runtime.patterns import load


class _AnswerLLM:
    """直接给最终答案（不出 tool_calls）→ 子 Agent 一轮结束。"""

    async def achat(
        self, messages: list[dict[str, Any]], tools: Any = None, **kwargs: Any
    ) -> dict[str, Any]:
        sys = " ".join(str(m.get("content") or "") for m in messages[:2])
        if "子 Agent" in sys:
            return {"role": "assistant", "content": "子任务完成"}
        return {"role": "assistant", "content": "总结：子任务完成"}


def _run(pattern: dict, user_input: str = "go") -> BaseHarnessV2:
    h = BaseHarnessV2({}, {}, {}, {}, llm_client=_AnswerLLM(), tool_registry=None)
    h.PATTERNS = [pattern]
    load(h)
    asyncio.run(h.run(user_input))
    return h


def test_spawn_runs_a_real_subagent() -> None:
    h = _run({"pattern": "router", "routes": ["deploy=>ops"]}, "deploy")
    evs = h.patterns.events_for("orchestrator")
    done = [e["detail"] for e in evs if e["detail"].get("results")]
    assert done, f"必须真跑子 Agent，实际事件={evs}"
    results = done[0]["results"]
    assert results[0]["worker"] == "ops"
    assert results[0]["answer"] == "子任务完成", results


def test_fanout_runs_branches_concurrently() -> None:
    h = _run({"pattern": "parallel", "branches": ["a", "b", "c"]})
    evs = h.patterns.events_for("orchestrator")
    done = [e["detail"] for e in evs if e["detail"].get("results")]
    assert done, evs
    results = done[0]["results"]
    assert [r["worker"] for r in results] == ["a", "b", "c"]
    assert all(r["answer"] == "子任务完成" for r in results), results
