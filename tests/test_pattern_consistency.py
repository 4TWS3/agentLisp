"""US-42：口径三处一致（README / LANDED 注释 / 落地清单）的机器核对。

约定在 scripts/check_pattern_consistency.py，唯一真源在 runtime/patterns/__init__.py。
本测试跑真脚本，不复制判断逻辑。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_pattern_consistency.py"


def test_three_way_pattern_tally_is_consistent() -> None:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0, f"口径不一致：stdout={cp.stdout} stderr={cp.stderr[-400:]}"
