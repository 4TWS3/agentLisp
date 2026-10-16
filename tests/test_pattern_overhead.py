"""US-40 / US-41：模式接入开销与长跑稳定的守卫。

跑真脚本（1000 轮）。阈值：每轮 < 1ms；后 100 轮不显著慢于前 100 轮。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bench_pattern_overhead.py"


def test_pattern_overhead_and_stability() -> None:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr[-300:]
    assert "OK" in cp.stdout
