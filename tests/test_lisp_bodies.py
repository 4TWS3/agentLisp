"""模型 B：节点体用 Lisp 写，编译成 Python，作者不写 .py。

判据：
  1. 编译产物含 _al_node_<节点名> 函数，且是合法 Python；
  2. WORKFLOW 的节点带 'body' 函数对象（不是 handler 字符串）；
  3. 桥直接调用它跑通；
  4. (py/call "模块.函数" …) 能调宿主库；
  5. :handler 与 :body 同时给 -> 编译期拒绝。
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

pytestmark = pytest.mark.skipif(not RACKET, reason="racket 不可用")

BASE = """(define-agent demo
  (:model :provider "openai" :name "m" :system-prompt "s")
  (:tools (import-builtin read-file))
  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #f))
  (:state :fields ((facts :type dict) (draft :type str) (ok :type bool)))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #f :linter-check #f :test-runner "")
            (:correct :max-retries 1 :on-failure abort))
  (:workflow :entry {entry}
    :nodes ({nodes})
    :topology ((sequential ({order})))))
"""

NODES = """(facts :type computation
                    :body (hash "facts" (hash "revenue" 138000))
                    :output-fields (facts))
             (draft :type computation
                    :body (let ((f (hash-ref state "facts")))
                            (hash "draft" (format "营收 ~a" (hash-ref f "revenue"))))
                    :output-fields (draft))
             (gate :type computation
                   :body (hash "ok" (string-contains? (hash-ref state "draft" "") "营收"))
                   :output-fields (ok))"""


def _compile(
    tmp_path: Path, nodes: str = NODES, order: str = "facts draft gate", entry: str = "facts"
) -> subprocess.CompletedProcess:
    src = BASE.format(nodes=nodes, order=order, entry=entry)
    (tmp_path / "c.al").write_text(src, encoding="utf-8")
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


def test_lisp_body_compiles_to_python_function(tmp_path: Path) -> None:
    cp = _compile(tmp_path)
    assert cp.returncode == 0, cp.stderr[-500:]
    src = (tmp_path / "o.py").read_text(encoding="utf-8")
    ast.parse(src)  # 必须是合法 Python
    assert "def _al_node_facts(state):" in src
    assert "def _al_node_draft(state):" in src
    assert "from runtime import al_core as _al" in src
    # 声明的是函数对象，不是字符串指针
    assert "'body': _al_node_facts" in src


def test_lisp_body_runs_end_to_end(tmp_path: Path) -> None:
    cp = _compile(tmp_path)
    assert cp.returncode == 0, cp.stderr[-500:]
    # 仓库规则：测试不许改全局 sys.path（test_cr42_pitfall_guards 会拦）。
    # 用 spec_from_file_location 直接按路径加载产物。
    import importlib.util

    from runtime.langgraph_bridge import build_graph

    spec = importlib.util.spec_from_file_location("compiled_demo", tmp_path / "o.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    h = mod.DemoHarness()
    app = build_graph(h.WORKFLOW, handlers={}, state_fields=h.STATE_FIELDS)
    out = app.invoke({})
    assert out["facts"] == {"revenue": 138000}
    assert out["draft"] == "营收 138000"
    assert out["ok"] is True


def test_py_call_interop(tmp_path: Path) -> None:
    """完备性靠宿主互操作：(py/call "模块.函数" …) 直接调库。"""
    nodes = """(calc :type computation
                    :body (hash "facts" (py/call "json.loads" "{\\"revenue\\": 42}"))
                    :output-fields (facts))
             (gate :type computation
                   :body (hash "ok" #t)
                   :output-fields (ok))"""
    cp = _compile(tmp_path, nodes=nodes, order="calc gate", entry="calc")
    assert cp.returncode == 0, cp.stderr[-500:]
    src = (tmp_path / "o.py").read_text(encoding="utf-8")
    assert '_al.py_call("json.loads"' in src


def test_handler_and_body_are_mutually_exclusive(tmp_path: Path) -> None:
    nodes = """(facts :type computation
                    :handler "m.f"
                    :body (hash "facts" (hash "a" 1))
                    :output-fields (facts))"""
    cp = _compile(tmp_path, nodes=nodes, order="facts")
    assert cp.returncode != 0
    assert "不能同时给 :handler 与 :body" in cp.stderr


def test_computation_without_handler_or_body_fails(tmp_path: Path) -> None:
    nodes = """(facts :type computation :output-fields (facts))"""
    cp = _compile(tmp_path, nodes=nodes, order="facts")
    assert cp.returncode != 0
    assert "必须给 :handler 或 :body" in cp.stderr
