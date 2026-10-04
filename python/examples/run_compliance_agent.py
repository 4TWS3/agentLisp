"""Example: Running a workflow with custom tool handlers."""

from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path

from agentlisp_runtime.engine import AgentEngine
from agentlisp_runtime.loader import AgentLoader
from agentlisp_runtime.models import (
    Agent,
    AtomicAction,
    ExecutionContext,
    Step,
    Tool,
    Workflow,
)


class KnowledgeBaseTool:
    _DOCS = {
        "doc-1": "政务信息化项目申报需包含项目背景、建设目标、投资估算三部分。",
        "doc-2": "项目总投资超过1000万需由省级评审委员会审批。",
        "doc-3": "合规性审查规则集版本 2.3 生效日期 2026-01-01。",
    }

    async def query(self, keyword: str, limit: int = 10) -> dict:
        hits = [
            {"id": k, "content": v}
            for k, v in self._DOCS.items()
            if keyword in v
        ]
        return {"query": keyword, "hits": hits[:limit], "total": len(hits)}


class ComplianceTool:
    async def verify(self, document_id: str, rules: list) -> dict:
        passed = random.random() > 0.3
        issues = [] if passed else [{"rule": rules[0] if rules else "r0", "severity": "high"}]
        return {"document": document_id, "pass": passed, "issues": issues}


class ReportTool:
    async def generate(self, data: dict, template: str) -> dict:
        return {
            "report": f"REPORT[{template}]:\n" + json.dumps(data, ensure_ascii=False, indent=2),
            "path": f"/tmp/report-{Path(template).stem}.md",
        }


def build_compliance_agent() -> Agent:
    return Agent(
        name="compliance-reviewer",
        purpose="政务项目申报书合规性审查 Agent",
        tools=[
            Tool(name="knowledge", description="知识库检索"),
            Tool(name="compliance", description="合规性校验"),
            Tool(name="report", description="报告生成"),
        ],
        workflows=[
            Workflow(
                name="document-review",
                triggers=["manual", "schedule"],
                steps=[
                    Step(
                        id="collect",
                        action=AtomicAction(
                            name="search", target="knowledge", method="query",
                            params=["项目申报书", 50],
                        ),
                        next="verify",
                    ),
                    Step(
                        id="verify",
                        action=AtomicAction(
                            name="verify", target="compliance", method="verify",
                            params=["project-book.docx", ["rule-1", "rule-2", "rule-3"]],
                        ),
                        next="report",
                    ),
                    Step(
                        id="report",
                        action=AtomicAction(
                            name="gen", target="report", method="generate",
                            params=[{"status": "done"}, "standard-template"],
                        ),
                        next=None,
                    ),
                ],
            )
        ],
    )


async def main() -> None:
    agent = build_compliance_agent()
    engine = AgentEngine(
        agent,
        tool_handlers={
            "knowledge": KnowledgeBaseTool(),
            "compliance": ComplianceTool(),
            "report": ReportTool(),
        },
    )
    ctx = ExecutionContext()
    result = await engine.run_workflow("document-review", ctx)

    print("=" * 60)
    print(f"Run ID:     {result.run_id}")
    print(f"Status:     {result.status.value}")
    print(f"Duration:   {result.total_duration_ms:.1f} ms")
    print(f"Steps:      {len(result.steps)}")
    print("=" * 60)
    for step in result.steps:
        print(f"  [{step.status.value:>7}] {step.step_id:<10}  {step.duration_ms:>7.1f} ms")
        if step.output:
            out = json.dumps(step.output, ensure_ascii=False)
            print(f"             output: {out[:160]}{'...' if len(out) > 160 else ''}")


if __name__ == "__main__":
    asyncio.run(main())
