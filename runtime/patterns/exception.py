"""exception handler：重试/退避策略（契约 CT-EXCEPTION-01）。

设计 v2 §11：只做确定性注入；不放宽既有保护（取更保守者）。
"""

from __future__ import annotations

from typing import Any


class ExceptionHandler:
    kind = "exception"

    def __init__(self, spec: dict) -> None:
        self.spec = spec
        self.retries = int(spec.get("retries") or 0)
        self.backoff = str(spec.get("backoff") or "exponential")

    def on_init(self, harness: Any, others: list[str]) -> None:
        if self.retries <= 0:
            raise ValueError("exception 需要正整数 :retries（契约 CT-EXCEPTION-01）")
        if self.backoff not in ("none", "linear", "exponential"):
            raise ValueError(
                f"exception 的 :backoff={self.backoff!r} 非法；允许 none/linear/exponential"
            )

    def before_turn(self, harness: Any, ctx: dict) -> dict:
        msgs = ctx.setdefault("messages", [])
        directive = {
            "role": "system",
            "content": (
                f"[pattern:exception] retries={self.effective_retries(harness)} "
                f"backoff={self.backoff}（与既有 correct.max_retries 取更保守者）"
            ),
        }
        if not any(
            isinstance(m, dict) and "pattern:exception" in str(m.get("content", "")) for m in msgs
        ):
            msgs.insert(0, directive)
        return ctx

    def on_tool_call(self, harness: Any, call: dict) -> tuple[bool, str]:
        return True, ""

    def after_turn(self, harness: Any, ctx: dict) -> dict:
        return ctx

    # ---- 纯函数（契约断言直接打它）----
    def effective_retries(self, harness: Any) -> int:
        """生效重试次数 = min(pattern.retries, harness.correct.max_retries)（不放宽保护）。"""
        cfg = getattr(harness, "harness_config", None) or {}
        correct = cfg.get("correct") if isinstance(cfg, dict) else None
        base = None
        if isinstance(correct, dict):
            base = correct.get("max_retries")
        if isinstance(base, int) and base > 0:
            return min(self.retries, base)
        return self.retries

    def policy(self, harness: Any) -> dict:
        return {"retries": self.effective_retries(harness), "backoff": self.backoff}
