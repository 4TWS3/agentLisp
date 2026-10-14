"""US-30：槽位模型核对脚本接进门禁。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_slot_model.py"


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
    assert cp.returncode == 0, "槽位模型不一致：stdout=" + cp.stdout + " stderr=" + cp.stderr[-400:]
