"""跑 tianji 切片（全能力）：agentLisp 声明图 -> LangGraph 执行 -> agentLisp 跑节点。

覆盖：computation handler / subagent 按名路由 / conditional-loop 重试 / :state :reducer 累积

用法：
  DEEPSEEK_API_KEY=... python3 examples/tianji_slice/run_pipeline.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "examples" / "tianji_slice" / "dist"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DIST))

from agent import TianjiSliceHarness  # noqa: E402
from writer import WriterHarness  # noqa: E402

from runtime.langgraph_bridge import build_graph  # noqa: E402
from runtime.llm_client import OpenAIClient  # noqa: E402


def _llm() -> OpenAIClient:
    return OpenAIClient(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com/v1",
    )


def report_node(state: dict) -> dict:
    """report 节点：把通过的草稿压成一句话。"""
    draft = str(state.get("draft") or "")
    h = TianjiSliceHarness(llm_client=_llm())
    prompt = (
        f"草稿：\n{draft}\n\n评审：{state.get('review_reason', '')}\n\n"
        "把上面压成一句话结论（<=60 字），必须保留一个具体数字。"
    )
    trace = asyncio.run(h.run(prompt))
    return {"report": str(trace.final_answer or "")}


def build() -> object:
    main_h = TianjiSliceHarness()
    return build_graph(
        main_h.WORKFLOW,
        handlers={
            # loop 判定：评审没过就重写
            "draft__while": lambda s: not bool(s.get("review_ok")),
            "report": report_node,
        },
        # 传工厂而不是类：子 Agent 也要拿到真 LLM，否则会用 MockLLMClient（实测踩过）
        agents={"writer": lambda: WriterHarness(llm_client=_llm())},
        state_fields=main_h.STATE_FIELDS,
    )


def main() -> None:
    app = build()
    out = asyncio.run(app.ainvoke({}))
    print("=== 事实 ===")
    print(json.dumps(out.get("facts"), ensure_ascii=False))
    print("\n=== 草稿 ===")
    print(str(out.get("draft", ""))[:400])
    print("\n=== 评审 ===")
    print("ok:", out.get("review_ok"), "| reason:", out.get("review_reason"))
    print("累积 sections 条数:", len(out.get("sections") or []))
    print("\n=== 结论 ===")
    print(str(out.get("report", ""))[:300])


if __name__ == "__main__":
    main()
