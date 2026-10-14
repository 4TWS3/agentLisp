"""US-35 提交门禁的存在性与同源性守卫。

门禁的行为由 .githooks/pre-commit -> scripts/git-gate.sh 实现。
本测试守住三点（约定要变成机器拦，不靠人记）：
  1. 门禁链路文件存在且可执行；
  2. pytest 路径来自唯一真源 tools/test_paths.txt（经 tools/verify_local.sh）；
  3. Racket 用 CI 同款命令 raco test compiler/tests/。
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "git-gate.sh"
HOOK = ROOT / ".githooks" / "pre-commit"
INSTALLER = ROOT / "scripts" / "install_git_hooks.sh"
VERIFY_LOCAL = ROOT / "tools" / "verify_local.sh"
PATHS_FILE = ROOT / "tools" / "test_paths.txt"


def test_gate_chain_files_exist_and_are_executable() -> None:
    """门禁链路三件必须存在且可执行；缺一件 = 门禁失效。"""
    for p in (GATE, HOOK, INSTALLER):
        assert p.is_file(), f"门禁链路缺文件：{p}"
        assert os.access(p, os.X_OK), f"门禁链路文件不可执行：{p}"


def test_hook_execs_gate() -> None:
    """pre-commit 必须真的调用门禁脚本，不能只占位。"""
    assert "scripts/git-gate.sh" in HOOK.read_text(encoding="utf-8")


def test_gate_uses_single_source_pytest_paths() -> None:
    """pytest 路径必须走唯一真源，避免「本地绿、CI 红」。"""
    assert "tools/verify_local.sh" in GATE.read_text(encoding="utf-8")
    assert PATHS_FILE.is_file(), "缺唯一真源 tools/test_paths.txt"
    assert "tools/test_paths.txt" in VERIFY_LOCAL.read_text(encoding="utf-8")


def test_gate_runs_ci_same_racket_command() -> None:
    """Racket 门禁命令与 CI 的 compiler-tests job 同款。"""
    assert "raco test compiler/tests/" in GATE.read_text(encoding="utf-8")


def test_installer_sets_hooks_path() -> None:
    """安装器必须把 .githooks 设为生效路径（否则 hook 只是躺在版本库里）。"""
    text = INSTALLER.read_text(encoding="utf-8")
    assert "core.hooksPath" in text
    assert ".githooks" in text
