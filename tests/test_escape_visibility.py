"""逃逸口可见：:handler 节点必须编译期告警，并在 WORKFLOW 标记 escaped。

理由：agentLisp 唯一被证明的价值是「强制纪律」。逃逸能免费绕过，
纪律就是空话。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "compiler" / "main.rkt"
_BUNDLED = ROOT / ".racket" / "bin" / "racket"
RACKET = "racket" if shutil.which("racket") else (str(_BUNDLED) if _BUNDLED.exists() else None)

pytestmark = pytest.mark.skipif(not RACKET, reason="racket 不可用")

SRC = """(define-agent esc
  (:model :provider "openai" :name "m" :system-prompt "s")
  (:tools (import-builtin read-file))
  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #f))
  (:state :fields ((a :type str) (b :type str)))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #f :linter-check #f :test-runner "")
            (:correct :max-retries 1 :on-failure abort))
  (:workflow :entry x
    :nodes ((x :type computation :handler "m.f" :output-fields (a))
            (y :type computation :body (hash "b" "1") :output-fields (b)))
    :topology ((edge x y))))
"""


def _compile(tmp_path: Path):
    p = tmp_path / "e.al"
    p.write_text(SRC, encoding="utf-8")
    out = tmp_path / "e.py"
    return subprocess.run(
        [RACKET, str(MAIN), "-i", str(p), "-o", str(out), "--force"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    ), out


def test_handler_node_warns_at_compile(tmp_path: Path) -> None:
    cp, _ = _compile(tmp_path)
    assert cp.returncode == 0, cp.stderr[-500:]
    assert "逃逸出契约" in cp.stderr
    assert "节点 x" in cp.stderr
    # :body 节点不该告警
    assert "节点 y 逃逸" not in cp.stderr


def test_artifact_marks_escaped(tmp_path: Path) -> None:
    cp, out = _compile(tmp_path)
    assert cp.returncode == 0
    src = out.read_text(encoding="utf-8")
    assert "'escaped': True" in src
    assert "'escaped': False" in src
