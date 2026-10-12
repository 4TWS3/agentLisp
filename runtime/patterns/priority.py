"""priority handler：按 criteria 排序候选（契约 CT-PRIORITY-01）。

确定性、可断言、无 IO（设计 v2 §11：只做注入式行为）。
"""

from __future__ import annotations

from typing import Any


class PriorityHandler:
    kind = "priority"

    def __init__(self, spec: dict) -> None:
        self.spec = spec
        self.criteria = str(spec.get("criteria") or "")
        self.levels = int(spec.get("levels") or 3)

    # ---- 钩子 ----
    def on_init(self, harness: Any, others: list[str]) -> None:
        if not self.criteria:
            raise ValueError("priority 缺少必需键 :criteria（契约 CT-PRIORITY-01）")

    def before_turn(self, harness: Any, ctx: dict) -> dict:
        """在上下文最前面注入一条确定性指令（可被断言）。"""
        msgs = ctx.setdefault("messages", [])
        directive = {
            "role": "system",
            "content": (
                f"[pattern:priority] criteria={self.criteria} levels={self.levels}；"
                f"候选动作按 {self.criteria} 降序执行，缺失该字段者保持声明顺序"
            ),
        }
        if not any(
            isinstance(m, dict) and "pattern:priority" in str(m.get("content", "")) for m in msgs
        ):
            msgs.insert(0, directive)
        return ctx

    def on_tool_call(self, harness: Any, call: dict) -> tuple[bool, str]:
        return True, ""

    def after_turn(self, harness: Any, ctx: dict) -> dict:
        return ctx

    # ---- 纯函数（契约里的 order 断言直接打它）----
    def order(self, candidates: list[dict]) -> list[dict]:
        """按 criteria 降序；缺失该键的元素保持相对顺序（稳定排序的实现方式）。"""
        if not self.criteria:
            return list(candidates)
        with_key = [c for c in candidates if self.criteria in c]
        without = [c for c in candidates if self.criteria not in c]
        try:
            with_key.sort(key=lambda c: c[self.criteria], reverse=True)
        except TypeError:
            return list(candidates)
        return with_key + without
