"""四角色标准检查器接入测试套件（标准 A2：关键约定必须有测试）。

三条判据：
  1. 检查器全过（退出码 0）；
  2. 注册表封闭：--list 报出的条数 == 注册条数（12）；
  3. 能拦住：未登记的 id 必须被拒（退出码 2）——
     防止检查器退化成「永远通过」。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools" / "standards_check.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )


def test_standards_check_all_pass() -> None:
    cp = _run()
    assert cp.returncode == 0, f"标准检查未全过：\n{cp.stdout[-1500:]}\n{cp.stderr[-300:]}"


def test_registry_listed_and_closed() -> None:
    cp = _run("--list")
    assert cp.returncode == 0, cp.stderr[-300:]
    # 条数写死是**故意的**：新增判据必须同时改这里，从而强制「登记 + 有人看过」。
    # 若只想加判据而不想改测试，说明你在绕过封闭枚举。
    assert "共 18 条" in cp.stdout, f"注册条数异常：{cp.stdout[-300:]}"


def test_unknown_check_id_is_rejected() -> None:
    """能拦住才叫判据。"""
    cp = _run("--only", "ZZ")
    assert cp.returncode == 2, f"未登记 id 未被拒：rc={cp.returncode}"
    assert "未登记" in cp.stdout
