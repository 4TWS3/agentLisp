"""US-53：节点声明效应等级（F-AMS-8）。

判据：节点可声明 :effect；non_revertible 在并发（:pattern parallel）中必须串行（编译期拦）。
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "compiler" / "main.rkt"
_BUNDLED = ROOT / ".racket" / "bin" / "racket"
RACKET = "racket" if shutil.which("racket") else (str(_BUNDLED) if _BUNDLED.exists() else None)

pytestmark = pytest.mark.skipif(not RACKET, reason="racket 不可用（PATH 与 .racket/bin 均未找到）")

BASE = """(define-agent eff
  (:model :provider "anthropic" :name "m" :system-prompt "s")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #t)
            (:correct :max-retries 2 :on-failure abort))
  {extra})
"""

GOOD = "(:workflow :entry deploy :nodes ((deploy :type agent :effect non_revertible)))"
PARALLEL = '(:pattern :kind parallel :config (:markers ("p") :branches ("a" "b")))'


def _compile(tmp_path: Path, extra: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "c.al").write_text(BASE.format(extra=extra), encoding="utf-8")
    assert RACKET is not None
    return subprocess.run(
        [RACKET, str(MAIN), "-i", str(tmp_path / "c.al"), "-o", str(tmp_path / "o.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def test_effect_is_emitted(tmp_path: Path) -> None:
    cp = _compile(tmp_path, GOOD)
    assert cp.returncode == 0, cp.stderr[-400:]
    src = (tmp_path / "o.py").read_text(encoding="utf-8")
    ast.parse(src)
    m = re.search(r"self\.WORKFLOW: Dict\[str, Any\] = (.+)", src)
    assert m
    wf = ast.literal_eval(m.group(1))
    assert wf["nodes"][0]["effect"] == "non_revertible"


def test_non_revertible_with_parallel_fails(tmp_path: Path) -> None:
    cp = _compile(tmp_path, PARALLEL + "\n  " + GOOD)
    assert cp.returncode != 0
    assert "non_revertible" in cp.stderr and "串行" in cp.stderr


def test_unknown_effect_fails(tmp_path: Path) -> None:
    cp = _compile(tmp_path, "(:workflow :entry a :nodes ((a :type agent :effect magic)))")
    assert cp.returncode != 0
    assert ":effect" in cp.stderr
