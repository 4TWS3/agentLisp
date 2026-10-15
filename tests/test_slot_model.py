"""US-30 / US-31：槽位模型与防膨胀规则的守卫测试。

约定在 scripts/check_slot_model.py。
US-31 要求：新增槽位必须同时新增运行时调用点，否则失败。本测试证明它「能拦住」。
按路径加载模块（坑 #15：测试里不改全局 sys.path）。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_slot_model.py"


def _mod():
    spec = importlib.util.spec_from_file_location("check_slot_model_mod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_slot_model_is_consistent() -> None:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0, "槽位模型不一致：" + cp.stdout + cp.stderr[-400:]


def test_slot_without_call_point_is_rejected() -> None:
    """US-31：只加槽位、不加调用点 -> 失败。"""
    mod = _mod()
    slots = dict(mod.SLOTS)
    slots["ghost"] = "无调用点"
    problems = mod.check(slots=slots)
    assert any("防膨胀" in p for p in problems), problems


def test_kind_slot_outside_slots_is_rejected() -> None:
    """kind 声明了 SLOTS 之外的槽位 -> 失败。"""
    mod = _mod()
    kind_slots = {k: list(v) for k, v in mod.KIND_SLOTS.items()}
    kind_slots["priority"] = ["ghost"]
    problems = mod.check(kind_slots=kind_slots)
    assert any("槽位不在 SLOTS" in p for p in problems), problems


def test_missing_call_point_substring_is_rejected() -> None:
    """槽位的调用点证据在 runtime 里找不到 -> 失败。"""
    mod = _mod()
    evidence = dict(mod.SLOT_EVIDENCE)
    evidence["order"] = ("patterns.NOPE(",)
    problems = mod.check(slot_evidence=evidence)
    assert any("无运行时调用点" in p for p in problems), problems
