"""loop/recur 与宏：补齐「Python 没有 TCO」和「语言不可扩展」两个短板。"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "compiler" / "main.rkt"
_BUNDLED = ROOT / ".racket" / "bin" / "racket"
RACKET = "racket" if shutil.which("racket") else (str(_BUNDLED) if _BUNDLED.exists() else None)

pytestmark = pytest.mark.skipif(not RACKET, reason="racket 不可用")

BASE = """(define-agent demo
  (:model :provider "openai" :name "m" :system-prompt "s")
  (:tools (import-builtin read-file))
  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #f))
  {macros}
  (:lisp {lisp})
  (:state :fields ((n :type int) (total :type int) (flag :type str)))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #f :linter-check #f :test-runner "")
            (:correct :max-retries 1 :on-failure abort))
  (:workflow :entry start
    :nodes ((start :type computation :body {body} :output-fields (n total flag)))
    :topology ()))
"""


def _run(tmp_path: Path, body: str, macros: str = "", lisp: str = "") -> dict:
    src = BASE.format(body=body, macros=macros, lisp=lisp)
    p = tmp_path / "c.al"
    p.write_text(src, encoding="utf-8")
    out = tmp_path / "o.py"
    cp = subprocess.run(
        [RACKET, str(MAIN), "-i", str(p), "-o", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr[-800:]
    spec = importlib.util.spec_from_file_location("loop_" + tmp_path.name, out)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from runtime.langgraph_bridge import build_graph

    h = mod.DemoHarness()
    return build_graph(h.WORKFLOW, handlers={}, state_fields=h.STATE_FIELDS).invoke({})


def test_loop_iterates_without_stack_growth(tmp_path: Path) -> None:
    """1e5 次迭代在递归下必然爆栈；while 循环不会。"""
    lisp = "(define (sum-to n) (loop ((i 0) (acc 0)) (if (< i n) (recur (+ i 1) (+ acc i)) acc)))"
    out = _run(tmp_path, '(hash "total" (sum-to 100000) "n" 100000)', lisp=lisp)
    assert out["total"] == 4999950000


def test_loop_emits_while_true(tmp_path: Path) -> None:
    lisp = "(define (f n) (loop ((i 0)) (if (< i n) (recur (+ i 1)) i)))"
    _run(tmp_path, '(hash "total" (f 3) "n" 3)', lisp=lisp)
    assert "while True:" in (tmp_path / "o.py").read_text(encoding="utf-8")


def test_macro_expands_in_node_body(tmp_path: Path) -> None:
    macros = '(:macro (unless (c body) `(if (not ,c) ,body "no")))'
    out = _run(tmp_path, '(hash "flag" (unless (> 10 100) "小"))', macros=macros)
    assert out["flag"] == "小"


def test_macro_expands_in_lisp_helper(tmp_path: Path) -> None:
    macros = "(:macro (inc (x) `(+ ,x 1)))"
    lisp = "(define (twice n) (inc (inc n)))"
    out = _run(tmp_path, '(hash "total" (twice 40) "n" 0)', macros=macros, lisp=lisp)
    assert out["total"] == 42


def test_macro_is_hygienic(tmp_path: Path) -> None:
    """模板引入的绑定不许捕获调用方同名变量。

    不卫生时 (f 5) 会得到 101（s 被模板的 let 捕获）；
    卫生时模板的 s 改名为 s_m0，调用方的 s 保持 5 -> 6。
    """
    macros = "(:macro (with-s (v body) `(let ((s ,v)) ,body)))"
    lisp = "(define (f s) (with-s 100 (+ s 1)))"
    out = _run(tmp_path, '(hash "total" (f 5) "n" 5)', macros=macros, lisp=lisp)
    assert out["total"] == 6, out["total"]
    src = (tmp_path / "o.py").read_text(encoding="utf-8")
    assert "s_m0 = 100" in src, "模板绑定必须被改名"


def test_macro_arity_mismatch_is_loud(tmp_path: Path) -> None:
    macros = '(:macro (unless (c body) `(if (not ,c) ,body "no")))'
    src = BASE.format(body='(hash "flag" (unless (> 1 0)))', macros=macros, lisp="")
    p = tmp_path / "c.al"
    p.write_text(src, encoding="utf-8")
    cp = subprocess.run(
        [RACKET, str(MAIN), "-i", str(p), "-o", str(tmp_path / "o.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode != 0
    assert "需要 2 个参数" in cp.stderr
