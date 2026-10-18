"""确定性评审节点：检查草稿是否合格（模拟 tianji 的章节校验）。

不收 LLM，避免「谁打分」引入噪声。返回 sections（列表，供 :reducer append 累积）。
"""

from __future__ import annotations

import re

MIN_CHARS = 80


def review(state: dict) -> dict:
    draft = str(state.get("draft") or "")
    reasons: list[str] = []
    if len(draft) < MIN_CHARS:
        reasons.append(f"太短（{len(draft)} < {MIN_CHARS} 字）")
    if not re.search(r"\d", draft):
        reasons.append("没有任何数字（研判必须有事实依据）")
    ok = not reasons
    return {
        "review_ok": ok,
        "review_reason": "通过" if ok else "；".join(reasons),
        "sections": [draft] if ok else [],
    }
