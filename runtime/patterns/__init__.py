"""模式运行时（设计 v2 §3-§7）。

职责：读产物里的 self.PATTERNS → 按 kind 载入 handler → 提供确定性、可观测的注入式行为。

规则（设计 v2 §4）：
  * 未知 kind 启动即报错（与编译期同口径，不许静默降级）
  * 未声明模式 → 不载入任何 handler，行为与不带模式完全一致（向后兼容）
  * 跨组按声明顺序串行；同组多成员在 on_init 报错并点名双方（§6 冲突矩阵）
"""

from __future__ import annotations

from typing import Any, Protocol

# 具体 handler（顶部导入：无循环依赖 —— 各 handler 只依赖 typing）
from runtime.patterns.declarative import DECLARATIVE
from runtime.patterns.exception import ExceptionHandler
from runtime.patterns.priority import PriorityHandler

# 已落地的 kind（每落地一个加一个；判据 A11 要求：LANDED 里每个 kind 必须有
#   (a) docs/spec/pattern_runtime_contracts/<kind>.md
#   (b) tests/patterns_runtime/test_<kind>.py
#   (c) 测试里引用该契约 id
LANDED: set[str] = {
    "priority",
    "exception",
    "reflect",
    "evaluator",
    "guardrails-safety",
    "hitl",
    "rag",
    "reasoning",
}

# 冲突分组（设计 v2 §6）：同组内只能选一个
GROUPS: dict[str, set[str]] = {
    "编排": {"chain", "parallel", "planner", "router"},
    "状态": {"fsm", "goal-setting"},
    "评估": {"evaluator", "decomposer"},
    "质量": {"reflect", "exception"},
    "安全": {"guardrails-safety", "hitl"},
    "知识": {"rag", "topic-model", "learning"},
    "资源": {"resource-aware", "exploration"},
    "协作": {"a2a", "decomposition"},
}


class PatternHandler(Protocol):
    kind: str

    def on_init(self, harness: Any, others: list[str]) -> None: ...
    def before_turn(self, harness: Any, ctx: dict) -> dict: ...
    def on_tool_call(self, harness: Any, call: dict) -> tuple[bool, str]: ...
    def after_turn(self, harness: Any, ctx: dict) -> dict: ...


class PatternRuntime:
    """载入后的运行时代理：挂在 harness.patterns 上。"""

    def __init__(self, harness: Any) -> None:
        self.harness = harness
        self.declared: list[dict] = list(getattr(harness, "PATTERNS", None) or [])
        self.handlers: list[PatternHandler] = []
        self._check_conflicts()
        self._instantiate()

    # ---- 冲突矩阵（§6）----
    def _check_conflicts(self) -> None:
        kinds = [p.get("pattern") for p in self.declared if isinstance(p, dict)]
        for group, members in GROUPS.items():
            hit = [k for k in kinds if k in members]
            if len(set(hit)) > 1:
                raise ValueError(
                    f"模式冲突：{sorted(set(hit))} 同属「{group}」组，只能选一个（设计 v2 §6）"
                )

    def _instantiate(self) -> None:
        # HANDLERS 在模块末尾定义；本方法在运行时调用，名字已解析

        for spec in self.declared:
            if not isinstance(spec, dict):
                continue
            kind = spec.get("pattern")
            if not kind:
                continue
            factory = HANDLERS.get(kind)
            if factory is None:
                raise ValueError(
                    f"未知模式 kind={kind!r}；已实现={sorted(HANDLERS)}（未实现不等于可用，禁止静默忽略）"
                )
            h = factory(spec)
            h.on_init(self.harness, [p.get("pattern") for p in self.declared])
            self.handlers.append(h)

    # ---- 钩子分发（顺序 = 声明顺序，确定性）----
    def before_turn(self, ctx: dict) -> dict:
        for h in self.handlers:
            ctx = h.before_turn(self.harness, ctx)
        return ctx

    def on_tool_call(self, call: dict) -> tuple[bool, str]:
        for h in self.handlers:
            ok, why = h.on_tool_call(self.harness, call)
            if not ok:
                return False, why
        return True, ""

    def after_turn(self, ctx: dict) -> dict:
        for h in self.handlers:
            ctx = h.after_turn(self.harness, ctx)
        return ctx

    # ---- 供 handler 复用的查询 ----
    def order(self, candidates: list[dict]) -> list[dict]:
        """按已载入的 priority handler 排序；未声明该模式时**原样返回**（反证口径）。"""
        for h in self.handlers:
            fn = getattr(h, "order", None)
            if callable(fn):
                return fn(candidates)
        return list(candidates)

    def retry_policy(self) -> dict:
        """按已载入的 exception handler 返回策略；未声明该模式时返回 {}（反证口径）。"""
        for h in self.handlers:
            fn = getattr(h, "policy", None)
            if callable(fn):
                return fn(self.harness)
        return {}

    def spec(self, kind: str) -> dict:
        for p in self.declared:
            if isinstance(p, dict) and p.get("pattern") == kind:
                return p
        return {}

    def api(self, kind: str) -> Any:
        """取已载入的某个 kind 的 handler（供契约测试打纯函数）；未载入则 KeyError。"""
        for h in self.handlers:
            if getattr(h, "kind", None) == kind:
                return h
        raise KeyError(
            f"未载入 kind={kind!r}；已载入={[getattr(x, 'kind', None) for x in self.handlers]}"
        )

    def landed(self) -> list[str]:
        return sorted({p.get("pattern") for p in self.declared if isinstance(p, dict)} & LANDED)


def load(harness: Any) -> PatternRuntime:
    """在 BaseHarnessV2.__init__ 末尾调用：把 self.PATTERNS 变成行为。"""
    rt = PatternRuntime(harness)
    harness.patterns = rt
    return rt


HANDLERS: dict[str, Any] = {
    "priority": PriorityHandler,
    "exception": ExceptionHandler,
}
HANDLERS.update(DECLARATIVE)  # 批 1 接线：reflect/evaluator/guardrails-safety/hitl/rag/reasoning
