"""批 2：10 个「轻量新增」模式 handler（router/chain/parallel/planner/decomposition/fsm/decomposer/exploration/resource-aware/goal-setting）。

共同点：确定性纯函数 + 上下文注入，无 IO（设计 v2 §11）。
键全部取自编译期注册表（合法键），不发明新键：
  router:routes  chain:steps  parallel:branches  planner:plan-size  decomposition:max-depth
  fsm:initial-state+states  decomposer:schema-fields  exploration:budget+convergence
  resource-aware:budget  goal-setting:goal
"""

from __future__ import annotations

from typing import Any

# 档位表（模块级常量：避免类属性可变默认值 RUF012）
_TIERS: dict[str, str] = {"low": "small", "mid": "medium", "medium": "medium", "high": "large"}


class _B2:
    kind = ""

    def __init__(self, spec: dict) -> None:
        self.spec = spec

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

    def summary(self) -> str:
        return ""


def _require(spec: dict, key: str) -> Any:
    if key not in spec or spec[key] in (None, "", []):
        raise ValueError(f"{key} 为必需键（见契约）")
    return spec[key]


class RouterHandler(_B2):
    kind = "router"

    def validate(self) -> None:
        routes = _require(self.spec, "routes")
        if not all("=>" in str(r) for r in routes):
            raise ValueError("router 的 :routes 每项须为 intent=>worker（契约 CT-ROUTER-01）")

    def summary(self) -> str:
        return f"routes={len(self.spec['routes'])} 条；按意图分发"

    def route(self, intent: str) -> str:
        for r in self.spec["routes"]:
            left, _, right = str(r).partition("=>")
            if left.strip() == intent:
                return right.strip()
        raise KeyError(f"router 未覆盖意图 {intent!r}")


class ChainHandler(_B2):
    kind = "chain"

    def validate(self) -> None:
        _require(self.spec, "steps")

    def summary(self) -> str:
        return f"steps={self.steps()}（串行，前步输出注入后步）"

    def steps(self) -> list[str]:
        return [str(s) for s in self.spec["steps"]]

    def next_step(self, index: int) -> str | None:
        s = self.steps()
        return s[index] if 0 <= index < len(s) else None


class ParallelHandler(_B2):
    kind = "parallel"

    def validate(self) -> None:
        _require(self.spec, "branches")

    def summary(self) -> str:
        return f"branches={self.branches()}（并行后归并）"

    def branches(self) -> list[str]:
        return [str(b) for b in self.spec["branches"]]

    def fan_in(self, results: list[Any]) -> list[Any]:
        if len(results) != len(self.branches()):
            raise ValueError("parallel：归并结果数须等于分支数（契约 CT-PARALLEL-01）")
        return list(results)


class PlannerHandler(_B2):
    kind = "planner"

    def validate(self) -> None:
        if int(_require(self.spec, "plan-size")) <= 0:
            raise ValueError("planner 的 :plan-size 须为正整数")

    def summary(self) -> str:
        return f"plan-size={self.plan_size()}；先计划后执行"

    def plan_size(self) -> int:
        return int(self.spec["plan-size"])

    def completion(self, done: int, total: int) -> float:
        return 0.0 if total <= 0 else round(done / total, 4)


class DecompositionHandler(_B2):
    kind = "decomposition"

    def validate(self) -> None:
        if int(_require(self.spec, "max-depth")) <= 0:
            raise ValueError("decomposition 的 :max-depth 须为正整数")

    def summary(self) -> str:
        return f"max-depth={self.max_depth()}；递归分解"

    def max_depth(self) -> int:
        return int(self.spec["max-depth"])

    def children(self, task: str, depth: int) -> list[str]:
        if depth > self.max_depth():
            raise ValueError(f"decomposition：depth={depth} 超过 max-depth={self.max_depth()}")
        return [f"{task}.{i}" for i in range(1, 3)]


class FsmHandler(_B2):
    kind = "fsm"

    def validate(self) -> None:
        _require(self.spec, "initial-state")
        states = _require(self.spec, "states")
        if not all("->" in str(s) and ":" in str(s) for s in states):
            raise ValueError("fsm 的 :states 每项须为 from->to:event（契约 CT-FSM-01）")

    def summary(self) -> str:
        return f"initial={self.initial_state()}；states={len(self.spec['states'])} 条迁移"

    def initial_state(self) -> str:
        return str(self.spec["initial-state"])

    def transition(self, state: str, event: str) -> str:
        for s in self.spec["states"]:
            left, _, right = str(s).partition(":")
            src, _, dst = left.partition("->")
            if src.strip() == state and right.strip() == event:
                return dst.strip()
        raise ValueError(f"fsm：非法迁移 state={state!r} event={event!r}")

    # ---- M2 接线：工具名即状态，非法迁移直接拦截 ----
    def on_tool_call(self, harness: Any, call: dict) -> tuple[bool, str]:
        name = str(call.get("tool_name") or "")
        if not name:
            return True, ""
        cur = getattr(self, "_state", None) or self.initial_state()
        try:
            nxt = self.transition(cur, name)
        except ValueError as e:
            return False, f"Harness Blocked: fsm 拒绝非法迁移（当前 {cur}，工具 {name}）{e}"
        self._state = nxt
        return True, ""


class DecomposerHandler(_B2):
    kind = "decomposer"

    def validate(self) -> None:
        _require(self.spec, "schema-fields")

    def summary(self) -> str:
        return f"schema-fields={self.schema_fields()}"

    def schema_fields(self) -> list[str]:
        return [str(f) for f in self.spec["schema-fields"]]

    def validate_payload(self, payload: dict) -> tuple[bool, list[str]]:
        missing = [f for f in self.schema_fields() if f not in payload]
        wrong_type = [
            f for f in self.schema_fields() if f in payload and not isinstance(payload[f], str)
        ]
        return (not missing and not wrong_type), missing + wrong_type


class ExplorationHandler(_B2):
    kind = "exploration"

    def validate(self) -> None:
        if int(_require(self.spec, "budget")) <= 0:
            raise ValueError("exploration 的 :budget 须为正整数")
        _require(self.spec, "convergence")

    def summary(self) -> str:
        return f"budget={self.budget()} convergence={self.convergence()}"

    def budget(self) -> int:
        return int(self.spec["budget"])

    def convergence(self) -> float:
        return float(self.spec["convergence"])

    def should_stop(self, spent: int, delta: float) -> bool:
        return spent >= self.budget() or delta <= self.convergence()


class ResourceAwareHandler(_B2):
    kind = "resource-aware"

    def validate(self) -> None:
        b = str(_require(self.spec, "budget")).lower()
        if b not in _TIERS:
            raise ValueError(
                "resource-aware 的 :budget ∈ {low, mid, high}（契约 CT-RESOURCE_AWARE-01）"
            )

    def on_init(self, harness: Any, others: list[str]) -> None:
        """M2 接线：把档位写进 model_config（部署方据此选模型）。"""
        super().on_init(harness, others)
        cfg = getattr(harness, "model_config", None)
        if isinstance(cfg, dict):
            cfg["tier"] = self.tier()

    def summary(self) -> str:
        return f"budget={self.budget()} → tier={self.tier()}"

    def budget(self) -> str:
        return str(self.spec["budget"]).lower()

    def tier(self) -> str:
        return _TIERS[self.budget()]


class GoalSettingHandler(_B2):
    kind = "goal-setting"

    def validate(self) -> None:
        _require(self.spec, "goal")

    def summary(self) -> str:
        return f"goal={self.goal()}；监控进度与偏差"

    def goal(self) -> str:
        return str(self.spec["goal"])

    def deviation(self, progress: float) -> bool:
        return progress < 1.0


B2_HANDLERS: dict[str, type] = {
    "router": RouterHandler,
    "chain": ChainHandler,
    "parallel": ParallelHandler,
    "planner": PlannerHandler,
    "decomposition": DecompositionHandler,
    "fsm": FsmHandler,
    "decomposer": DecomposerHandler,
    "exploration": ExplorationHandler,
    "resource-aware": ResourceAwareHandler,
    "goal-setting": GoalSettingHandler,
}
