"""US-04：(:state :fields …) -> 产物 STATE_FIELDS（F-AMS-3）。

判据：声明后产物含 STATE_FIELDS，运行期可读。
负例：重复块 / 缺 :fields / 缺 :type / 未知 :type -> 编译期失败。
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "compiler" / "main.rkt"
_BUNDLED = ROOT / ".racket" / "bin" / "racket"
RACKET = "racket" if shutil.which("racket") else (str(_BUNDLED) if _BUNDLED.exists() else None)

pytestmark = pytest.mark.skipif(not RACKET, reason="racket 不可用（PATH 与 .racket/bin 均未找到）")

BASE = """(define-agent st
  (:model :provider "anthropic" :name "m" :system-prompt "s")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #t)
            (:correct :max-retries 2 :on-failure abort))
  {extra})
"""


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


def test_state_fields_in_artifact(tmp_path: Path) -> None:
    cp = _compile(
        tmp_path,
        '(:state :fields ((metrics :type dict) (stage :type str :default "")))',
    )
    assert cp.returncode == 0, cp.stderr[-400:]
    src = (tmp_path / "o.py").read_text(encoding="utf-8")
    ast.parse(src)
    assert "self.STATE_FIELDS" in src
    assert '"metrics"' in src
    assert "'type': \"dict\"" in src
    assert "'default': \"\"" in src


def test_duplicate_state_block_fails(tmp_path: Path) -> None:
    cp = _compile(
        tmp_path,
        "(:state :fields ((a :type str)))\n  (:state :fields ((b :type str)))",
    )
    assert cp.returncode != 0
    assert ":state 块重复" in cp.stderr


def test_state_without_fields_fails(tmp_path: Path) -> None:
    cp = _compile(tmp_path, "(:state)")
    assert cp.returncode != 0
    assert ":fields" in cp.stderr


def test_field_without_type_fails(tmp_path: Path) -> None:
    cp = _compile(tmp_path, "(:state :fields ((a)))")
    assert cp.returncode != 0
    assert ":type" in cp.stderr


def test_unknown_field_type_fails(tmp_path: Path) -> None:
    cp = _compile(tmp_path, "(:state :fields ((a :type mystery)))")
    assert cp.returncode != 0
    assert "枚举" in cp.stderr
