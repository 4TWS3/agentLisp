"""US-28 / P2-2：注册表无悬空（孤儿条目收口）。

判据（B2）：注册表 kind 数 == 运行期 kind 数 + 显式非运行期 kind 数。
memory / multi-agent 由核心语法承载，登记为「非运行期」，不进 HANDLERS。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "compiler" / "pattern_registry.rkt"
_BUNDLED = ROOT / ".racket" / "bin" / "racket"
RACKET = "racket" if shutil.which("racket") else (str(_BUNDLED) if _BUNDLED.exists() else None)

pytestmark = pytest.mark.skipif(not RACKET, reason="racket 不可用（PATH 与 .racket/bin 均未找到）")


def _registry_kinds() -> set[str]:
    expr = (
        '(require (file "'
        + REG.as_posix()
        + '")) (displayln (string-join (map (lambda (k) (format "~a" k)) (pattern-kinds)) " "))'
    )
    cp = subprocess.run(
        [RACKET, "-e", expr],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr[-300:]
    return set(cp.stdout.strip().split())


def test_registry_equals_runtime_plus_non_runtime() -> None:
    """B2：注册表 = 运行期 kind + 显式非运行期 kind。无悬空。"""
    from runtime.patterns import CONTRACTED, NON_RUNTIME_KINDS

    got = _registry_kinds()
    want = set(CONTRACTED) | set(NON_RUNTIME_KINDS)
    assert got == want, (
        "注册表与运行期+非运行期不一致：仅注册="
        + str(sorted(got - want))
        + "；仅声明="
        + str(sorted(want - got))
    )


def test_every_handler_is_a_runtime_kind() -> None:
    """有 handler 但不在 KIND_SLOTS -> 悬空。"""
    from runtime.patterns import CONTRACTED, HANDLERS

    extra = set(HANDLERS) - set(CONTRACTED)
    assert not extra, "有 handler 但不在 KIND_SLOTS：" + str(sorted(extra))


def test_non_runtime_kinds_are_registered_with_reason() -> None:
    from runtime.patterns import NON_RUNTIME_KINDS

    assert set(NON_RUNTIME_KINDS) == {"memory", "multi-agent"}
    for kind, reason in NON_RUNTIME_KINDS.items():
        assert str(reason).strip(), "非运行期 kind 缺理由：" + kind
