"""B-01：现代 emitter 不可用时必须非 0 退出，不许静默回退 legacy。

判据（实测复现）：把 agentlisp_compiler.rkt 移走后编译，必须 rc=1 且打印 EMITTER MISSING。
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

pytestmark = pytest.mark.skipif(not RACKET, reason="racket 不可用（PATH 与 .racket/bin 均未找到）")

MINIMAL = """(define-agent c
  (:model :provider "anthropic" :name "m" :system-prompt "s")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #t)
            (:correct :max-retries 2 :on-failure abort)))
"""


def _run(compiler_dir: Path, tmp: Path) -> subprocess.CompletedProcess[str]:
    assert RACKET is not None
    return subprocess.run(
        [
            RACKET,
            str(compiler_dir / "main.rkt"),
            "-i",
            str(tmp / "x.al"),
            "-o",
            str(tmp / "x.py"),
        ],
        cwd=str(tmp),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def test_normal_compile_succeeds(tmp_path: Path) -> None:
    (tmp_path / "x.al").write_text(MINIMAL, encoding="utf-8")
    cp = _run(ROOT / "compiler", tmp_path)
    assert cp.returncode == 0, cp.stderr[-400:]
    assert (tmp_path / "x.py").exists()


def test_missing_modern_emitter_fails_loudly(tmp_path: Path) -> None:
    comp = tmp_path / "compiler"
    shutil.copytree(ROOT / "compiler", comp)
    # 必须连 compiled/ 一起删。原因（2026-10-17 CI 实测）：
    # main.rkt 被 raco 编译成 compiled/main_rkt.zo 后，define-runtime-path 里记的是
    # **构建时的绝对路径**。于是从 .zo 加载时，它去原仓库加载 agentlisp_compiler.rkt，
    # 而不是临时副本 → 源码删了也能跑，rc=0，测试在 CI 红、本机绿。
    shutil.rmtree(comp / "compiled", ignore_errors=True)
    (comp / "agentlisp_compiler.rkt").unlink()
    (tmp_path / "x.al").write_text(MINIMAL, encoding="utf-8")
    cp = _run(comp, tmp_path)
    assert cp.returncode == 1, f"必须非 0 退出，实际 {cp.returncode}"
    assert "EMITTER MISSING" in (cp.stdout + cp.stderr), "必须打印可见原因"
    assert not (tmp_path / "x.py").exists(), "失败时不许写出产物"
