"""US-39 / P2-7：C1 冻结文件追认的守卫。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_c1_freeze.py"


def test_c1_freeze_is_ratified() -> None:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0, "C1 有未追认的改动：" + cp.stdout + cp.stderr[-300:]
