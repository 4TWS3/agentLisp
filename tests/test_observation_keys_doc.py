"""US-24：观察值键文档必须覆盖 runtime 的真读键（机器核对）。

约定在 scripts/check_observation_keys_doc.py。本测试跑真脚本，不复制判断逻辑。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_observation_keys_doc.py"


def test_observation_keys_doc_covers_runtime_reads() -> None:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0, "文档漏键：stdout=" + cp.stdout + " stderr=" + cp.stderr[-400:]
