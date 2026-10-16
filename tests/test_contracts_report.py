"""US-12：21 份契约机器校验报告可跑且全过。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_contracts.py"


def test_contracts_report_is_green() -> None:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0, "契约校验有缺口：\n" + cp.stdout + cp.stderr[-300:]
    assert "21/21" in cp.stdout, cp.stdout[-300:]
