"""批 1 接线：6 个纯声明式模式 handler（reflect / evaluator / guardrails-safety / hitl / rag / reasoning）。

共同点：只做「确定性注入 + 纯函数查询」，无 IO（设计 v2 §11）。
合并到一个模块的原因：六者结构几乎相同；契约与测试仍按 kind 各一份（判据 A11 按 kind 校验）。
"""

from __future__ import annotations

from typing import Any


class _Base:
    kind = ""

    def __init__(self, spec: dict) -> None:
        self.spec = spec

    # ---- 生命周期 ----
    def on_init(self, harness: Any, others: list[str]) -> None:
        self.validate()

    def validate(self) -> None:
        return None

    def before_turn(self, harness: Any, ctx: dict) -> dict:
        msgs = ctx.setdefault("messages", [])
        marker = f"pattern:{self.kind}"
        if not any(isinstance(m, dict) and marker in str(m.get("content", "")) for m in msgs):
            msgs.insert(0, {"role": "system", "content": f"[{marker}] {self.summary()}"})
        return ctx

    def on_tool_call(self, harness: Any, call: dict) -> tuple[bool, str]:
        return True, ""

    def after_turn(self, harness: Any, ctx: dict) -> dict:
        return ctx

    # ---- 由子类实现 ----
    def summary(self) -> str:
        return ""


class ReflectHandler(_Base):
    kind = "reflect"

    def validate(self) -> None:
        if not self.spec.get("reviewer-agent"):
            raise ValueError("reflect 需要 :reviewer-agent（契约 CT-REFLECT-01）")

    def summary(self) -> str:
        return f"reviewer={self.spec['reviewer-agent']}；失败进入反思—修正回路"

    def config(self) -> dict:
        return {"reviewer": self.spec["reviewer-agent"]}


class EvaluatorHandler(_Base):
    kind = "evaluator"

    def thresholds(self) -> tuple[float, float]:
        t = self.spec.get("thresholds") or []
        if len(t) != 2:
            raise ValueError("evaluator 需要 :thresholds 两个值（契约 CT-EVALUATOR-01）")
        lo, hi = float(t[0]), float(t[1])
        if not (0.0 <= lo <= hi <= 1.0):
            raise ValueError("evaluator 阈值须在 [0,1] 且 lo <= hi")
        return lo, hi

    def summary(self) -> str:
        lo, hi = self.thresholds()
        return f"thresholds=({lo},{hi})"

    def evaluate(self, score: float) -> str:
        lo, hi = self.thresholds()
        if score >= hi:
            return "pass"
        return "rework" if score >= lo else "escalate"


class GuardrailsSafetyHandler(_Base):
    kind = "guardrails-safety"

    def validate(self) -> None:
        hooks = self.spec.get("hooks") or []
        if not hooks:
            raise ValueError(
                "guardrails-safety 需要 :hooks 三段钩子（契约 CT-GUARDRAILS_SAFETY-01）"
            )

    def summary(self) -> str:
        return f"hooks={self.stages()}"

    def stages(self) -> list[str]:
        return [str(h) for h in (self.spec.get("hooks") or [])]


class HitlHandler(_Base):
    kind = "hitl"

    def validate(self) -> None:
        if not self.spec.get("approval-before"):
            raise ValueError("hitl 需要 :approval-before（契约 CT-HITL-01）")

    def summary(self) -> str:
        return f"approval-before={self.stages()}"

    def stages(self) -> list[str]:
        v = self.spec.get("approval-before")
        return [str(x) for x in (v if isinstance(v, list) else [v])]

    def requires_approval(self, stage: str) -> bool:
        return stage in self.stages()

    def on_tool_call(self, harness: Any, call: dict) -> tuple[bool, str]:
        """M2 接线：approval-before 命中的工具，未带 approved=True 即拦截（真实生效）。"""
        name = str(call.get("tool_name") or "")
        args = call.get("args") or {}
        approved = bool(call.get("approved")) or bool(
            isinstance(args, dict) and args.get("approved")
        )
        if name and self.requires_approval(name) and not approved:
            return False, f"Harness Blocked: hitl 需要人工批准（阶段 {name}，契约 CT-HITL-01）"
        return True, ""


class RagHandler(_Base):
    kind = "rag"

    def validate(self) -> None:
        return None

    def summary(self) -> str:
        return "检索前置 + 证据回填（引用必须可验证）"

    def verify_evidence(self, answer: str, evidence_ids: list[str]) -> tuple[bool, str]:
        if not evidence_ids:
            return False, "rag：未提供任何证据 id（契约 CT-RAG-01）"
        hit = [e for e in evidence_ids if e and e in answer]
        if not hit:
            return False, f"rag：回答未引用任何证据 id（应有其一：{evidence_ids[:3]}）"
        return True, f"引用 {len(hit)} 条证据"


class ReasoningHandler(_Base):
    kind = "reasoning"

    def validate(self) -> None:
        t = str(self.spec.get("technique") or "")
        if t not in ("cot", "tree-of-thought", "tot"):
            raise ValueError(
                "reasoning 需要 :technique ∈ {cot, tree-of-thought}（契约 CT-REASONING-01）"
            )

    def summary(self) -> str:
        return f"technique={self.spec.get('technique')}；显式推理结构写入 trajectory"

    def technique(self) -> str:
        return str(self.spec["technique"])


DECLARATIVE: dict[str, type] = {
    "reflect": ReflectHandler,
    "evaluator": EvaluatorHandler,
    "guardrails-safety": GuardrailsSafetyHandler,
    "hitl": HitlHandler,
    "rag": RagHandler,
    "reasoning": ReasoningHandler,
}
