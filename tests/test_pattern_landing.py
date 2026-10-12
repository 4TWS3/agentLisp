"""21 个设计模式落地清单的守护测试。

三条判据：
  1. 生成器 rc=0（= 21/21 模式同时具备「宏定义 + 注册表 kind 条目」）；
  2. 清单不陈旧：重新生成后的内容与仓库里的文件**逐字节一致**；
  3. 清单内容可核对：21 行数据 + 5 个规格别名 + 两类宏文件路径。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pattern_landing_report.py"
REPORT = ROOT / "docs" / "spec" / "agentlisp_pattern_landing.md"


def _run() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )


def test_generator_reports_21_of_21() -> None:
    cp = _run()
    assert cp.returncode == 0, f"落地清单生成失败：\n{cp.stdout[-800:]}\n{cp.stderr[-400:]}"
    assert "21/21" in cp.stdout, f"未达 21/21：{cp.stdout[-300:]}"


def test_report_is_not_stale() -> None:
    before = REPORT.read_text(encoding="utf-8")
    cp = _run()
    assert cp.returncode == 0, cp.stdout[-300:]
    after = REPORT.read_text(encoding="utf-8")
    assert before == after, (
        "清单与代码不一致（生成物陈旧）：请运行 python3 scripts/pattern_landing_report.py 后提交"
    )


def test_report_lists_macro_sites_and_aliases() -> None:
    text = REPORT.read_text(encoding="utf-8")
    # 去掉可能的 \r：Windows 检出（autocrlf）会给行尾加 CR，splitlines 已处理，
    # 但显式 strip 更稳（该测试曾在 Windows 失败）。
    rows = [
        ln.replace("\r", "")
        for ln in text.splitlines()
        if ln.replace("\r", "").startswith("| ") and "`def" in ln
    ]
    assert len(rows) == 21, f"清单数据行应为 21，实际 {len(rows)}"
    for alias in (
        "defprioritized-agent",
        "defa2a-server",
        "defresilient-agent",
        "defapproval-agent",
        "defguarded-agent",
    ):
        assert alias in text, f"缺规格 BNF 别名：{alias}"
    assert "compiler/patterns_v2.rkt:" in text
    assert "compiler/patterns.rkt:" in text
    assert "compiler/pattern_registry.rkt:" in text
