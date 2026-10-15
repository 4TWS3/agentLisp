"""US-11：模式组合校验在编译期（F-AMS-4 / P1-3）。

判据：
  - 同组两个 kind -> 编译期失败（rc != 0），错误点名双方；
  - 跨组可编译；
  - 编译期的组数据与运行时 GROUPS 同源（机器比对，防两处实现分叉）。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "compiler" / "main.rkt"
REG = ROOT / "compiler" / "pattern_registry.rkt"
_BUNDLED = ROOT / ".racket" / "bin" / "racket"
RACKET = "racket" if shutil.which("racket") else (str(_BUNDLED) if _BUNDLED.exists() else None)
HAS_RACKET = RACKET is not None

pytestmark = pytest.mark.skipif(
    not HAS_RACKET, reason="racket 不可用（PATH 与 .racket/bin 均未找到）"
)


def _src(blocks: list[str]) -> str:
    head = [
        "(define-agent c",
        '  (:model :provider "anthropic" :name "m" :system-prompt "s")',
        "  (:tools (import-builtin bash))",
        '  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))',
        '  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))',
        "            (:verify :json-schema #t)",
        "            (:correct :max-retries 2 :on-failure abort))",
    ]
    return chr(10).join(head + blocks + [")", ""])


def _compile(tmp_path: Path, src: str) -> subprocess.CompletedProcess[str]:
    al = tmp_path / "c.al"
    al.write_text(src, encoding="utf-8")
    assert RACKET is not None
    return subprocess.run(
        [RACKET, str(MAIN), "-i", str(al), "-o", str(tmp_path / "c.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def test_same_group_is_compile_error(tmp_path: Path) -> None:
    """同组两 kind：编译期失败，且点名双方与组名。"""
    cp = _compile(
        tmp_path,
        _src(
            [
                '  (:pattern :kind chain :config (:markers ("a") :steps ("x")))',
                '  (:pattern :kind router :config (:markers ("b") :routes ("p=>q")))',
            ]
        ),
    )
    assert cp.returncode != 0, "同组两 kind 应在编译期失败，实际 rc=" + str(cp.returncode)
    assert "ERR_PATTERN_CONFLICT" in cp.stderr, cp.stderr[-400:]
    assert "chain" in cp.stderr and "router" in cp.stderr, cp.stderr[-400:]


def test_cross_group_compiles(tmp_path: Path) -> None:
    """跨组两 kind：可编译。"""
    cp = _compile(
        tmp_path,
        _src(
            [
                '  (:pattern :kind chain :config (:markers ("a") :steps ("x")))',
                '  (:pattern :kind fsm :config (:markers ("b") :initial-state "a" :states ("a->b:go")))',
            ]
        ),
    )
    assert cp.returncode == 0, cp.stderr[-400:]


def test_racket_groups_match_runtime_groups() -> None:
    """编译期 pattern-groups 与运行时 GROUPS 必须同源（防两处实现分叉）。"""
    assert RACKET is not None
    expr = (
        '(require (file "'
        + REG.as_posix()
        + '")) (displayln (string-join (map (lambda (g) (string-append (car g) ":" '
        + '(string-join (map (lambda (k) (format "~a" k)) (cdr g)) ","))) pattern-groups) ";"))'
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
    parsed: dict[str, list[str]] = {}
    for part in cp.stdout.strip().split(";"):
        if not part:
            continue
        name, _, members = part.partition(":")
        parsed[name] = sorted(members.split(","))
    from runtime.patterns import GROUPS

    want = {name: sorted(members) for name, members in GROUPS.items()}
    assert parsed == want, (
        "编译期组数据与运行时 GROUPS 不一致：" + repr(parsed) + " vs " + repr(want)
    )
