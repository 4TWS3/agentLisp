#!/usr/bin/env python3
"""US-30 槽位模型核对（F-AMS-6 / 决策 D3）。

唯一真源：runtime/patterns/__init__.py 的 SLOTS / KIND_SLOTS。
核对五件：
  1. KIND_SLOTS 与契约文件集合一致。
  2. 每个 kind 的槽位属于 SLOTS。
  3. LANDED = 占槽位非空；DECLARED_ONLY = 占槽位为空；两者是 CONTRACTED 的划分。
  4. 每个已实现槽位有运行时调用点（子串证据）。
  5. 每份契约写明槽位（canonical 行）。

退出码：0 = 全过；1 = 有缺口。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.patterns import (  # noqa: E402
    CONTRACTED,
    DECLARED_ONLY,
    KIND_SLOTS,
    LANDED,
    PENDING_SLOTS,
    SLOTS,
)

CONTRACTS = ROOT / "docs" / "spec" / "pattern_runtime_contracts"
RUNTIME = ROOT / "runtime"
BT = chr(96)

# 槽位 -> 运行时调用点证据（纯子串，避开正则转义）。证据必须真的出现。
SLOT_EVIDENCE: dict[str, tuple[str, ...]] = {
    "on_init": (".on_init(",),
    "before_turn": ("patterns.before_turn(",),
    "on_tool_call": ("patterns.on_tool_call(",),
    "verify": ("patterns.verify_observation(",),
    "evaluate": ('fn(float(observation["score"]))',),
    "order": ("patterns.order(",),
    "budget": ("patterns.retries_cap(", "patterns.turn_budget("),
}


def runtime_text() -> str:
    return chr(10).join(p.read_text(encoding="utf-8") for p in RUNTIME.rglob("*.py"))


def slot_line(slots: list[str]) -> str:
    if not slots:
        return "| **槽位** | 无（declaration-only） |"
    rendered = "、".join(BT + s + BT for s in sorted(slots))
    return "| **槽位** | " + rendered + " |"


def check() -> list[str]:
    problems: list[str] = []
    contract_kinds = {p.stem for p in CONTRACTS.glob("*.md")}
    if contract_kinds != CONTRACTED:
        problems.append(
            "KIND_SLOTS 与契约集合不一致：有契约无 kind="
            + str(sorted(contract_kinds - CONTRACTED))
            + "；有 kind 无契约="
            + str(sorted(CONTRACTED - contract_kinds))
        )
    for kind, slots in KIND_SLOTS.items():
        bad = set(slots) - set(SLOTS)
        if bad:
            problems.append(kind + ": 槽位不在 SLOTS：" + str(sorted(bad)))
    if {k for k, s in KIND_SLOTS.items() if s} != LANDED:
        problems.append("LANDED != 占槽位非空的 kind")
    if {k for k, s in KIND_SLOTS.items() if not s} != DECLARED_ONLY:
        problems.append("DECLARED_ONLY != 占槽位为空的 kind")
    if (LANDED & DECLARED_ONLY) or (LANDED | DECLARED_ONLY != CONTRACTED):
        problems.append("LANDED / DECLARED_ONLY 不构成 CONTRACTED 的划分")

    implemented = set(SLOTS) - PENDING_SLOTS
    if set(SLOT_EVIDENCE) != implemented:
        problems.append(
            "SLOT_EVIDENCE 未覆盖全部已实现槽位：缺 "
            + str(sorted(implemented - set(SLOT_EVIDENCE)))
        )
    text = runtime_text()
    for slot, evidences in SLOT_EVIDENCE.items():
        for ev in evidences:
            if ev not in text:
                problems.append("槽位 " + slot + " 无运行时调用点：缺子串 " + repr(ev))

    for kind, slots in KIND_SLOTS.items():
        path = CONTRACTS / (kind + ".md")
        if not path.is_file():
            continue
        want = slot_line(slots)
        if want not in path.read_text(encoding="utf-8"):
            problems.append(kind + ": 契约缺槽位行 " + repr(want))
    return problems


def main() -> int:
    problems = check()
    if problems:
        for p in problems:
            print("FAIL", p)
        return 1
    print(
        "OK 槽位模型：CONTRACTED="
        + str(len(CONTRACTED))
        + " LANDED="
        + str(len(LANDED))
        + " DECLARED_ONLY="
        + str(len(DECLARED_ONLY))
        + " SLOTS="
        + str(len(SLOTS))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
