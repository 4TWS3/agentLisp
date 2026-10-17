"""FR-EVO-3（US-48）：在线循环只读。

判据：:online-trace 开启时写元数据，且**绝不写回 .al 源码**。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from runtime.base_harness_v2 import BaseHarnessV2


class _H(BaseHarnessV2):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # 先设 EVOLUTION，再让父类 __init__ 读它（_load_evolution_contract）
        self.EVOLUTION = {
            "online_trace": True,
            "mutation_targets": [":skills"],
            "immutable_invariants": [":kv-alignment"],
            "verifier_gate": {
                "name": "t2-bench@v1.0",
                "min_pass_rate": 0.9,
                "mcnemar_p_threshold": 0.05,
            },
        }
        super().__init__(*args, **kwargs)


class _LLM:
    async def achat(
        self, messages: list[dict[str, Any]], tools: Any = None, **kwargs: Any
    ) -> dict[str, Any]:
        return {"role": "assistant", "content": "done", "tool_calls": None}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_online_trace_writes_metadata_and_leaves_source_untouched(
    tmp_path: Path, monkeypatch: object
) -> None:
    src = tmp_path / "agent.al"
    src.write_text("(define-agent ot)\n", encoding="utf-8")
    before = _sha(src)
    monkeypatch.setenv("AGENTLISP_ONLINE_TRACE_DIR", str(tmp_path / "traces"))  # type: ignore[attr-defined]

    h = _H({}, {}, {}, {}, llm_client=_LLM())
    trace = asyncio.run(h.run("go"))

    written = list((tmp_path / "traces").glob("*.json"))
    assert len(written) == 1, written
    payload = json.loads(written[0].read_text(encoding="utf-8"))
    assert payload["run_id"] == trace.run_id
    assert payload["evolution"]["online_trace"] is True
    assert "metadata only" in payload["note"]
    assert _sha(src) == before, "在线循环写回了 .al 源码"


def test_without_online_trace_writes_nothing(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setenv("AGENTLISP_ONLINE_TRACE_DIR", str(tmp_path / "traces"))  # type: ignore[attr-defined]
    h = BaseHarnessV2({}, {}, {}, {}, llm_client=_LLM())
    asyncio.run(h.run("go"))
    assert not (tmp_path / "traces").exists()
