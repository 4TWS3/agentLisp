"""US-33：契约栏位机器拦（判据 A12）的守卫测试。

约定在 tools/standards_check.py 的 _check_a12_contract_columns / _contract_columns_problems。
按路径加载模块（坑 #15：测试里不得改全局 sys.path）。既跑真判据，也证明它能拦住缺栏与空栏。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools" / "standards_check.py"

GOOD = (
    "| **id** | CT-X-01 |\n"
    "| **槽位** | order |\n"
    "| **输入** | a |\n"
    "| **期望（可观测）** | b |\n"
    "| **反证** | c |\n"
    "| **端口** | d |\n"
    "| **不承诺** | e |\n"
)


def _sc():
    # 坑 #15：用 importlib 按路径加载，不碰全局 sys.path
    spec = importlib.util.spec_from_file_location("standards_check_mod", CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a12_passes_on_complete_contract() -> None:
    assert _sc()._contract_columns_problems(GOOD) == []


def test_a12_detects_missing_column() -> None:
    broken = GOOD.replace("| **不承诺** | e |\n", "")
    problems = _sc()._contract_columns_problems(broken)
    assert any("不承诺" in p for p in problems), problems


def test_a12_detects_empty_column() -> None:
    broken = GOOD.replace("| **反证** | c |", "| **反证** |  |")
    problems = _sc()._contract_columns_problems(broken)
    assert any("反证" in p and "为空" in p for p in problems), problems


def test_a12_runs_green_on_repo() -> None:
    cp = subprocess.run(
        [sys.executable, str(CHECKER), "--only", "A12"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr[-300:]
