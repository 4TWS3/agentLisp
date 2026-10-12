"""CR-42 P-1：:pattern 构造落到语言层（注册表 + parser 校验 + checker 语义校验 + emitter 生成）。

判据（来自 docs/spec/cr42_pattern_language_level_design.md §6）：
- 合法 (:pattern …) 必须在产物里出现 PATTERNS 结构（不再只活在 system-prompt 文本）；
- 非法 config 必须**编译期**报错（缺必需键 / 未知 kind / 未知键）；
- 无模式时 PATTERNS 为空列表（不破坏既有产物）。
"""

from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HAS_RACKET = shutil.which("racket") is not None
COMPILER = ROOT / "compiler" / "agentlisp_compiler.rkt"

BLOCKS = """((:model :provider "anthropic" :name "m" :system-prompt "s")
           (:tools (import-builtin bash))
           (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))
           (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                     (:verify :json-schema #t)
                     (:correct :max-retries 2 :on-failure abort)))"""


def _run_racket(tmp_path: Path, pattern_block: str) -> subprocess.CompletedProcess[str]:
    src = textwrap.dedent(
        f"""        #lang racket/base
        (require racket/string (file "{COMPILER.as_posix()}"))
        (define form (cons 'define-agent (cons 'a (append '{BLOCKS} '{pattern_block}))))
        (with-handlers ([(lambda (e) #t) (lambda (e) (eprintf "EXN: ~a" (exn-message e)) (exit 1))])
          (display (compile-agent-lisp form)))
        """
    )
    probe = tmp_path / "probe.rkt"
    probe.write_text(src, encoding="utf-8")
    return subprocess.run(
        ["racket", str(probe)], cwd=ROOT, capture_output=True, text=True, timeout=120
    )


pytestmark = pytest.mark.skipif(not HAS_RACKET, reason="racket not on PATH")


def test_legal_pattern_emits_patterns_structure(tmp_path: Path) -> None:
    cp = _run_racket(
        tmp_path,
        '((:pattern :kind priority :config (:markers ("m1" "m2") :criteria "按用户影响面" :levels 2)))',
    )
    assert cp.returncode == 0, cp.stderr[-400:]
    assert "self.PATTERNS: List[Dict[str, Any]]" in cp.stdout
    assert "'pattern': \"priority\"" in cp.stdout or "'pattern': 'priority'" in cp.stdout
    # 生成的 Python 必须语法合法
    import ast

    ast.parse(cp.stdout)


def test_no_pattern_emits_empty_list(tmp_path: Path) -> None:
    cp = _run_racket(tmp_path, "()")
    assert cp.returncode == 0, cp.stderr[-400:]
    assert "self.PATTERNS: List[Dict[str, Any]] = []" in cp.stdout


def test_missing_required_key_is_compile_error(tmp_path: Path) -> None:
    cp = _run_racket(tmp_path, "((:pattern :kind priority :config (:levels 2)))")
    assert cp.returncode != 0
    assert "缺少必需 config 键" in cp.stderr


def test_unknown_kind_is_compile_error(tmp_path: Path) -> None:
    cp = _run_racket(tmp_path, "((:pattern :kind nope :config ()))")
    assert cp.returncode != 0
    assert "未知模式 kind" in cp.stderr


def test_unknown_config_key_is_checker_error(tmp_path: Path) -> None:
    cp = _run_racket(tmp_path, '((:pattern :kind priority :config (:markers ("m") :typo 1)))')
    assert cp.returncode != 0
    assert "ERR_PATTERN_CONFIG" in cp.stderr
