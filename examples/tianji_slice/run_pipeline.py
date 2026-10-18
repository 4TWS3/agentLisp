"""跑 tianji 切片：agentLisp 声明图 -> LangGraph 执行 -> agentLisp 跑每个节点。

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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples" / "tianji_slice" / "dist"))

from agent import TianjiSliceHarness  # noqa: E402

from runtime.langgraph_bridge import build_graph  # noqa: E402
from runtime.llm_client import OpenAIClient  # noqa: E402


def _llm() -> OpenAIClient:
    return OpenAIClient(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com/v1",
    )


def agent_node(system: str, out_key: str, prompt_of):
    """一个 agent 节点 = 起一个 agentLisp harness 跑一次。"""

    async def node(state: dict) -> dict:
        h = TianjiSliceHarness(llm_client=_llm())
        h.model_config["system_prompt"] = system
        prompt = prompt_of(state)
        trace = await h.run(prompt)
        return {out_key: trace.final_answer}

    return node


BASE = "你是经营研判分析师。结论只能基于给定事实，不得编造数字。"


def build() -> object:
    # WORKFLOW 是实例属性（在 __init__ 里赋），不是类属性。
    workflow = TianjiSliceHarness().WORKFLOW
    return build_graph(
        workflow,
        {
            # facts 不在这里：它由 :handler "examples.tianji_slice.metrics.compute" 自动导入
            "value_judge": agent_node(
                BASE,
                "value_judgment",
                lambda s: "事实：\n"
                + json.dumps(
                    {k: v for k, v in s.items() if k != "messages"}, ensure_ascii=False, indent=2
                )
                + "\n\n请做第一层【价值判断】：这家企业的经营质量如何？三段：结论/依据/风险。",
            ),
            "operator_eval": agent_node(
                BASE,
                "operator_evaluation",
                lambda s: f"事实：{json.dumps(s.get('facts', {}), ensure_ascii=False)}\n"
                f"价值判断：{s.get('value_judgment', '')}\n\n"
                "请做第二层【经营者评价】：管理层动作是否匹配当前阶段？三段。",
            ),
            "improve": agent_node(
                BASE,
                "improvement_plan",
                lambda s: f"事实：{json.dumps(s.get('facts', {}), ensure_ascii=False)}\n"
                f"经营者评价：{s.get('operator_evaluation', '')}\n\n"
                "请给出【经营改善】建议：3 条可执行动作，每条带预期效果。",
            ),
            "report": agent_node(
                BASE,
                "report",
                lambda s: "把以下三段整合成一段 200 字以内的经营研判：\n"
                f"价值判断：{s.get('value_judgment', '')}\n"
                f"经营者评价：{s.get('operator_evaluation', '')}\n"
                f"改善建议：{s.get('improvement_plan', '')}",
            ),
        },
    )


def main() -> None:
    app = build()
    out = asyncio.run(app.ainvoke({}))
    print("=== 节点产出 ===")
    for k in ("months", "revenue_trend_pct", "net_margin_last_pct", "value_judgment"):
        if k in out:
            print(f"[{k}] {str(out[k])[:160]}")
    print("\n=== 最终报告 ===")
    print(str(out.get("report", ""))[:600])


if __name__ == "__main__":
    main()
