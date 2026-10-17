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

if hasattr(sys.stdout, "reconfigure"):
    # Windows 默认 cp1252：脚本里有中文，不重设会 UnicodeEncodeError（CI 实测）
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.patterns import (  # noqa: E402
    CONTRACTED,
    DECLARED_ONLY,
    DECLARED_ONLY_REASON,
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


def _derive(kind_slots: dict[str, list[str]]) -> tuple[set[str], set[str], set[str]]:
    landed = {k for k, s in kind_slots.items() if s}
    declared_only = {k for k, s in kind_slots.items() if not s}
    return landed, declared_only, set(kind_slots)


def check(
    *,
    slots: dict[str, str] | None = None,
    pending: set[str] | None = None,
    kind_slots: dict[str, list[str]] | None = None,
    slot_evidence: dict[str, tuple[str, ...]] | None = None,
    declared_reason: dict[str, str] | None = None,
    contracts_dir: Path | None = None,
    runtime_source: str | None = None,
) -> list[str]:
    """US-31 防膨胀规则入口。参数可注入，便于守卫测试证明「能拦住」。

    防膨胀规则（D3）：槽位只能由运行时调用点定义。
    新增槽位 = 新增一个真实调用点（slot_evidence 里的子串）+ 一条断言。
    只加槽位、不加调用点 -> 失败。禁止先加槽位再加实现。
    """
    slots = SLOTS if slots is None else slots
    pending = PENDING_SLOTS if pending is None else pending
    kind_slots = KIND_SLOTS if kind_slots is None else kind_slots
    slot_evidence = SLOT_EVIDENCE if slot_evidence is None else slot_evidence
    declared_reason = DECLARED_ONLY_REASON if declared_reason is None else declared_reason
    contracts_dir = CONTRACTS if contracts_dir is None else contracts_dir
    runtime_source = runtime_text() if runtime_source is None else runtime_source

    landed, declared_only, contracted = _derive(kind_slots)
    problems: list[str] = []
    contract_kinds = {p.stem for p in contracts_dir.glob("*.md")}
    if contract_kinds != contracted:
        problems.append(
            "KIND_SLOTS 与契约集合不一致：有契约无 kind="
            + str(sorted(contract_kinds - contracted))
            + "；有 kind 无契约="
            + str(sorted(contracted - contract_kinds))
        )
    for kind, kind_slot_list in kind_slots.items():
        bad = set(kind_slot_list) - set(slots)
        if bad:
            problems.append(kind + ": 槽位不在 SLOTS：" + str(sorted(bad)))
    if (landed & declared_only) or (landed | declared_only != contracted):
        problems.append("LANDED / DECLARED_ONLY 不构成 CONTRACTED 的划分")

    # US-26 / P2-1：声明层必须有定性（无第三态）。
    if set(declared_reason) != declared_only:
        problems.append(
            "声明层定性不全：缺 "
            + str(sorted(declared_only - set(declared_reason)))
            + "；多 "
            + str(sorted(set(declared_reason) - declared_only))
        )
    for kind, reason in declared_reason.items():
        if not str(reason).strip():
            problems.append("声明层定性为空：" + kind)

    # 防膨胀（US-31）：已实现槽位必须一一有调用点证据；证据不得多余。
    implemented = set(slots) - pending
    missing = sorted(implemented - set(slot_evidence))
    extra = sorted(set(slot_evidence) - implemented)
    if missing:
        problems.append(
            "防膨胀：已实现槽位缺调用点证据（新增槽位必须同时新增调用点）：" + str(missing)
        )
    if extra:
        problems.append("防膨胀：调用点证据含未声明的槽位：" + str(extra))
    for slot, evidences in slot_evidence.items():
        for ev in evidences:
            if ev not in runtime_source:
                problems.append("槽位 " + slot + " 无运行时调用点：缺子串 " + repr(ev))

    for kind, kind_slot_list in kind_slots.items():
        path = contracts_dir / (kind + ".md")
        if not path.is_file():
            continue
        want = slot_line(kind_slot_list)
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
