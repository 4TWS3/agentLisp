"""编排调度器（F-AMS-7）：唯一决策点 select_next(state) -> Action。

批 1：chain + planner（顺序类）。
决策只看 state（步数），不读时间/随机 -> 确定性可断言。
批 2/3（router / parallel / decomposition）待做，见 docs/handoff。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Action:
    """一个动作。kind ∈ {step, spawn, fanout, finish}。"""

    kind: str
    worker: str | None = None
    task: str | None = None
    branches: tuple[str, ...] = ()
    report: dict[str, Any] = field(default_factory=dict)

    def as_event(self) -> dict[str, Any]:
        return {
            "action": self.kind,
            "worker": self.worker,
            "task": self.task,
            "branches": list(self.branches),
            "report": dict(self.report),
        }


def build_orchestrator(runtime: Any) -> Orchestrator | None:
    """有编排 kind（chain / planner）时返回编排器；否则 None（走原循环）。"""
    o = Orchestrator(runtime)
    return o if o.active else None


class Orchestrator:
    """批 1：chain 按步骤推进；planner 先计划后执行。"""

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        self.chain = _handler(runtime, "chain")
        self.planner = _handler(runtime, "planner")

    @property
    def active(self) -> bool:
        return self.chain is not None or self.planner is not None

    def select_next(self, state: dict[str, Any]) -> Action:
        i = int(state.get("step_index", 0))
        if self.chain is not None:
            step = self.chain.next_step(i)
            if step is not None:
                return Action("step", task=step)
            return Action("finish", report={"kind": "chain", "steps": self.chain.steps()})
        if self.planner is not None:
            size = int(self.planner.plan_size())
            if i == 0:
                return Action("step", task="plan")
            if i >= size:
                return Action(
                    "finish",
                    report={"kind": "planner", "completion": self.planner.completion(i, size)},
                )
            return Action("step", task="plan-step-" + str(i))
        return Action("step")


def _handler(runtime: Any, kind: str) -> Any:
    for h in getattr(runtime, "handlers", []):
        if getattr(h, "kind", "") == kind:
            return h
    return None
