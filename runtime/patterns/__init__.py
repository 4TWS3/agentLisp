"""模式运行时（设计 v2 §3-§7）。

职责：读产物里的 self.PATTERNS → 按 kind 载入 handler → 提供确定性、可观测的注入式行为。

规则（设计 v2 §4）：
  * 未知 kind 启动即报错（与编译期同口径，不许静默降级）
  * 未声明模式 → 不载入任何 handler，行为与不带模式完全一致（向后兼容）
  * 跨组按声明顺序串行；同组多成员在 on_init 报错并点名双方（§6 冲突矩阵）
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

# 具体 handler（顶部导入：无循环依赖 —— 各 handler 只依赖 typing）
from runtime.patterns.declarative import DECLARATIVE
from runtime.patterns.declarative_b2 import B2_HANDLERS
from runtime.patterns.declarative_b3 import B3_HANDLERS
from runtime.patterns.exception import ExceptionHandler
from runtime.patterns.priority import PriorityHandler

logger = logging.getLogger(__name__)

# ---- 槽位模型（F-AMS-6 / 决策 D3）：口径唯一真源 ----
# 口径短语（README / 本注释 / docs/spec/agentlisp_pattern_landing.md 三处逐字一致）：
#   契约 21 / 落地 13 / 声明层 8
#
#   SLOTS         = 行为槽位。防膨胀规则（D3）：槽位只能由运行时的**真实调用点**定义。
#   KIND_SLOTS    = 每个 kind 占用的槽位。空 = declaration-only（声明层）。
#   LANDED        = 占槽位非空的 kind（= 引擎真消费）。派生，不手写第二份。
#   DECLARED_ONLY = 占槽位为空的 kind。显式登记，不假装生效（不变式 I1）。
#   CONTRACTED    = 有契约 + 运行时测试的 kind（= KIND_SLOTS 全部；判据 A11 要求
#                     (a) docs/spec/pattern_runtime_contracts/<kind>.md
#                     (b) tests/patterns_runtime/test_<kind>.py
#                     (c) 测试里引用该契约 id）。
#
# 实测修正（2026-10-14，US-30）：D3 的 8 个已实现槽位含 after_turn，但
# PatternRuntime.after_turn 全仓无调用点（grep 零命中）→ 按 D3 自己的防膨胀规则，
# after_turn 不是槽位，已删。故已实现 7 个槽位 + orchestrate 待实现。
# 通用 base 注入（所有 kind 都有的 before_turn 摘要）不算槽位占用，否则 21 个全非空、
# 槽位模型失去意义。
#
# 核对：python3 scripts/check_slot_model.py
SLOTS: dict[str, str] = {
    "on_init": "PatternRuntime._instantiate -> handler.on_init",
    "before_turn": "BaseHarnessV2.build_context -> PatternRuntime.before_turn",
    "on_tool_call": "BaseHarnessV2.call_tool -> PatternRuntime.on_tool_call",
    "verify": "BaseHarnessV2.verify -> PatternRuntime.verify_observation",
    "evaluate": "verify_observation 的 evaluator 分派 -> handler.evaluate",
    "order": "BaseHarnessV2.build_context -> PatternRuntime.order",
    "budget": "retries_cap + turn_budget",
    "orchestrate": "待实现（F-AMS-7 select_next）",
}

PENDING_SLOTS: set[str] = {"orchestrate"}

# 每个 kind 占用的槽位。只算「引擎按 kind 分派、且改变引擎行为」的调用点。
KIND_SLOTS: dict[str, list[str]] = {
    "priority": ["order"],
    "exception": ["budget"],
    "exploration": ["budget"],
    "resource-aware": ["on_init"],
    "hitl": ["on_tool_call"],
    "fsm": ["on_tool_call"],
    "rag": ["verify"],
    "decomposer": ["verify"],
    "evaluator": ["evaluate", "verify"],
    "reflect": ["verify"],
    "guardrails-safety": ["verify"],
    "reasoning": ["verify"],
    "goal-setting": ["verify"],
    # ---- 声明层（declaration-only）：handler 在，但引擎不调其行为 ----
    "a2a": [],
    "chain": [],
    "decomposition": [],
    "learning": [],
    "parallel": [],
    "planner": [],
    "router": [],
    "topic-model": [],
}

LANDED: set[str] = {k for k, s in KIND_SLOTS.items() if s}
DECLARED_ONLY: set[str] = {k for k, s in KIND_SLOTS.items() if not s}
CONTRACTED: set[str] = set(KIND_SLOTS)

# 声明层定性（US-26 / P2-1）：每个声明层 kind 必须给「为什么不落地」。
# 判据 G2：无第三态 —— 每个 kind 要么占槽位（LANDED），要么在这里有理由（DECLARED_ONLY）。
# 机器核对：scripts/check_slot_model.py 要求键集 == DECLARED_ONLY 且理由非空。
DECLARED_ONLY_REASON: dict[str, str] = {
    "router": "待 P4 编排接线（F-AMS-7 select_next；引擎目前不按 kind 选择下一动作）",
    "chain": "待 P4 编排接线（步骤顺序由编排器驱动）",
    "parallel": "待 P4 编排接线（分支扇出/归并由编排器驱动）",
    "planner": "待 P4 编排接线（先出计划再执行由编排器驱动）",
    "decomposition": "待 P4 编排接线（递归分解与 :multiagent 协调）",
    "topic-model": "声明层：聚类结果无引擎消费点；需要端口与编排节点头",
    "a2a": "声明层：跨 Agent 消息无引擎消费点；需要端口与编排节点头",
    "learning": "声明层：写回技能层无引擎消费点；需要端口与回合结束钩子",
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
        # M3 观测：每次模式介入留痕（可断言、可评审；设计 v2 §3 L5）
        self.events: list[dict] = []
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

        seen: set[str] = set()
        for spec in self.declared:
            if not isinstance(spec, dict):
                continue
            kind = spec.get("pattern")
            if not kind:
                continue
            if kind in seen:
                # 同一 kind 出现多次 → 幂等（只载入一个 handler，设计 v2 §6）
                logger.debug("[Pattern] 重复声明 kind=%s，已跳过", kind)
                continue
            seen.add(kind)
            factory = HANDLERS.get(kind)
            if factory is None:
                raise ValueError(
                    f"未知模式 kind={kind!r}；已实现={sorted(HANDLERS)}（未实现不等于可用，禁止静默忽略）"
                )
            h = factory(spec)
            h.on_init(self.harness, [p.get("pattern") for p in self.declared])
            self.handlers.append(h)

    # ---- US-14：handler 抛错不得拖垮 Agent ----
    def _handler_error(self, kind: str, hook: str, exc: Exception) -> None:
        """留痕，不抛出（P1-3a）。

        增强类钩子（before_turn / after_turn / order / budget）：跳过该 handler，用原值。
        安全类钩子（on_tool_call / verify）：按失败拒绝（fail-closed），不静默放行。
        """
        logger.exception("[Pattern] %s.%s 抛错，已捕获", kind, hook)
        self._record(kind, hook + "-error", {"error": f"{type(exc).__name__}: {exc}"})

    # ---- 钩子分发（顺序 = 声明顺序，确定性）----
    def before_turn(self, ctx: dict) -> dict:
        for h in self.handlers:
            kind = getattr(h, "kind", "?")
            try:
                ctx = h.before_turn(self.harness, ctx)
            except Exception as exc:  # 故意兜底
                self._handler_error(kind, "before_turn", exc)
        return ctx

    def on_tool_call(self, call: dict) -> tuple[bool, str]:
        for h in self.handlers:
            kind = getattr(h, "kind", "?")
            try:
                ok, why = h.on_tool_call(self.harness, call)
            except Exception as exc:  # 安全钩子：抛错按拒绝
                self._handler_error(kind, "on_tool_call", exc)
                why = f"模式 {kind} 的 on_tool_call 抛错，按失败拒绝（留痕）"
                self._record(kind, "on_tool_call", {"blocked": True, "why": why, "call": call})
                return False, why
            if not ok:
                self._record(kind, "on_tool_call", {"blocked": True, "why": why, "call": call})
                return False, why
            self._record(kind, "on_tool_call", {"blocked": False, "tool": call.get("tool_name")})
        return True, ""

    # ---- M3 观测 ----
    def _record(self, kind: str, hook: str, detail: dict) -> None:
        self.events.append({"kind": kind, "hook": hook, "detail": detail})
        logger.info("[Pattern] %s.%s %s", kind, hook, detail)
        # 优先级 3：有 OTel tracer 时同步发事件（与 SRS NFR-OBS-1 共用同一个 tracer）
        tracer = getattr(self.harness, "otel_tracer", None)
        if tracer is not None:
            try:
                tracer.on_step(
                    getattr(self.harness, "run_id", "-"),
                    len(self.events),
                    f"pattern.{kind}.{hook}",
                    detail,
                )
            except Exception:
                # 失败必须留痕（不得静默）
                logger.warning("[Pattern] OTel 事件发送失败", exc_info=True)

    def events_for(self, kind: str) -> list[dict]:
        return [e for e in self.events if e["kind"] == kind]

    def after_turn(self, ctx: dict) -> dict:
        for h in self.handlers:
            kind = getattr(h, "kind", "?")
            try:
                ctx = h.after_turn(self.harness, ctx)
            except Exception as exc:  # 故意兜底
                self._handler_error(kind, "after_turn", exc)
        return ctx

    # ---- 供 handler 复用的查询 ----
    def order(self, candidates: list[dict]) -> list[dict]:
        """按已载入的 priority handler 排序；未声明该模式时**原样返回**（反证口径）。"""
        for h in self.handlers:
            fn = getattr(h, "order", None)
            if callable(fn):
                kind = getattr(h, "kind", "?")
                try:
                    return fn(candidates)
                except Exception as exc:  # 增强钩子：跳过
                    self._handler_error(kind, "order", exc)
                    return list(candidates)
        return list(candidates)

    def retry_policy(self) -> dict:
        """按已载入的 exception handler 返回策略；未声明该模式时返回 {}（反证口径）。"""
        for h in self.handlers:
            fn = getattr(h, "policy", None)
            if callable(fn):
                kind = getattr(h, "kind", "?")
                try:
                    return fn(self.harness)
                except Exception as exc:  # 增强钩子：跳过
                    self._handler_error(kind, "retry_policy", exc)
                    return {}
        return {}

    def verify_observation(self, observation: dict) -> tuple[bool, str]:
        """US-14 外壳：handler 或内部分派抛错时按失败拒绝并留痕，不拖垮 Agent。"""
        try:
            return self._verify_observation_impl(observation)
        except Exception as exc:  # 安全钩子：抛错按拒绝
            self._handler_error("?", "verify_observation", exc)
            return False, "模式 verify_observation 抛错，按失败拒绝（留痕）"

    def _verify_observation_impl(self, observation: dict) -> tuple[bool, str]:
        """M2 接线：观察值门控。声明了 rag 时，回答必须引用证据 id（契约 CT-RAG-01）。

        未声明相关模式 → 直接放行（向后兼容）。
        """
        for h in self.handlers:
            fn = getattr(h, "verify_evidence", None)
            if callable(fn) and isinstance(observation, dict):
                answer = str(observation.get("answer") or observation.get("final_answer") or "")
                ids = observation.get("evidence_ids") or []
                if answer or ids:
                    return fn(answer, list(ids))
        # decomposer：观察值里的结构化字段必须齐全（契约 CT-DECOMPOSER-01）
        for h in self.handlers:
            fn = getattr(h, "validate_payload", None)
            if callable(fn) and isinstance(observation, dict):
                payload = observation.get("fields") or observation.get("payload")
                if isinstance(payload, dict):
                    ok, bad = fn(payload)
                    if not ok:
                        return (
                            False,
                            f"decomposer：字段不齐或类型错：{bad}（契约 CT-DECOMPOSER-01）",
                        )
        # evaluator：观察值带 score 时按双阈值判定（契约 CT-EVALUATOR-01）
        for h in self.handlers:
            fn = getattr(h, "evaluate", None)
            if callable(fn) and isinstance(observation, dict) and "score" in observation:
                try:
                    verdict = fn(float(observation["score"]))
                except (TypeError, ValueError):
                    continue
                if verdict != "pass":
                    return (
                        False,
                        f"evaluator：score={observation['score']} → {verdict}（契约 CT-EVALUATOR-01）",
                    )
        # ---- M2 批 B：reflect / guardrails-safety / reasoning / goal-setting 观察门 ----
        kinds = {getattr(h, "kind", None): h for h in self.handlers}
        if isinstance(observation, dict):
            if "reflect" in kinds and not observation.get("reviewer"):
                self._record("reflect", "verify", {"missing": "reviewer"})
                return False, "reflect：缺 reviewer 复核结论（契约 CT-REFLECT-01）"
            if "guardrails-safety" in kinds and not observation.get("audit"):
                self._record("guardrails-safety", "verify", {"missing": "audit"})
                return False, "guardrails-safety：缺审计记录 audit（契约 CT-GUARDRAILS_SAFETY-01）"
            if "reasoning" in kinds and not observation.get("reasoning"):
                self._record("reasoning", "verify", {"missing": "reasoning"})
                return False, "reasoning：缺显式推理结构（契约 CT-REASONING-01）"
            if "goal-setting" in kinds and "progress" in observation:
                _gs = kinds["goal-setting"]
                try:
                    _dev = _gs.deviation(float(observation["progress"]))
                except (TypeError, ValueError):
                    _dev = False
                if _dev:
                    self._record("goal-setting", "verify", {"progress": observation["progress"]})
                    return False, "goal-setting：进度未达目标（契约 CT-GOAL_SETTING-01）"
        return True, ""

    def retries_cap(self, base: int) -> int:
        """M2 接线：生效重试上限 = min(既有, 模式策略)；未声明 exception 时返回 base。"""
        p = self.retry_policy()
        r = p.get("retries") if isinstance(p, dict) else None
        return min(base, r) if isinstance(r, int) and r > 0 else base

    def turn_budget(self, base: int) -> int:
        """M2 接线：轮次上限 = min(既有, exploration.budget)；未声明则返回 base。"""
        for h in self.handlers:
            b = getattr(h, "budget", None)
            if callable(b):
                kind = getattr(h, "kind", "?")
                try:
                    v = int(b())
                except Exception as exc:  # 增强钩子：跳过
                    self._handler_error(kind, "turn_budget", exc)
                    continue
                if v > 0:
                    return min(base, v)
        return base

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


def load(harness: Any, adapters: dict | None = None) -> PatternRuntime:
    """在 BaseHarnessV2.__init__ 末尾调用：把 self.PATTERNS 变成行为。

    M3：adapters 可把某 kind 的 Mock 端口换成生产适配器，例如
    {"learning": FileSkillStore(dir)} —— 未提供时仍用内存 Mock（并告警）。
    """
    rt = PatternRuntime(harness)
    for kind, port in (adapters or {}).items():
        for h in rt.handlers:
            if getattr(h, "kind", None) == kind:
                for attr in ("store", "retriever", "bus"):
                    if hasattr(h, attr):
                        setattr(h, attr, port)
    harness.patterns = rt
    return rt


HANDLERS: dict[str, Any] = {
    "priority": PriorityHandler,
    "exception": ExceptionHandler,
}
HANDLERS.update(DECLARATIVE)  # 批 1 接线：reflect/evaluator/guardrails-safety/hitl/rag/reasoning
HANDLERS.update(
    B2_HANDLERS
)  # 批 2：router/chain/parallel/planner/decomposition/fsm/decomposer/exploration/
# 批 3：topic-model / a2a / learning（Mock 端口驱动，见 ports.py）
HANDLERS.update(B3_HANDLERS)
