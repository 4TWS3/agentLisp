"""确定性事实计算（模拟 tianji 的 olap_facts 节点）。

不做 LLM 判断，只算数。输出 JSON，供 Agent 消费。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def compute(_state: dict | None = None) -> dict:
    """节点实现契约：收 state，返回 dict（LangGraph 的状态增量）。"""
    rows = list(csv.DictReader((HERE / "data" / "monthly.csv").open(encoding="utf-8")))
    rev = [float(r["revenue"]) for r in rows]
    cost = [float(r["cost"]) for r in rows]
    gross = [r - c for r, c in zip(rev, cost, strict=True)]
    net_margin = [g / r for g, r in zip(gross, rev, strict=True)]
    burn = [c - r for r, c in zip(rev, cost, strict=True)]
    cash = float(rows[-1]["cash"])

    avg_burn = sum(burn) / len(burn)
    runway = cash / avg_burn if avg_burn > 0 else None
    return {
        "months": len(rows),
        "revenue_first": rev[0],
        "revenue_last": rev[-1],
        "revenue_trend_pct": round((rev[-1] / rev[0] - 1) * 100, 1),
        "net_margin_first_pct": round(net_margin[0] * 100, 1),
        "net_margin_last_pct": round(net_margin[-1] * 100, 1),
        "loss_months": sum(1 for b in burn if b > 0),
        "avg_monthly_burn": round(avg_burn, 0),
        "cash_now": cash,
        "runway_months": round(runway, 1) if runway else None,
    }


if __name__ == "__main__":
    print(json.dumps(compute(), ensure_ascii=False, indent=2))
