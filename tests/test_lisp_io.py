"""节点体的两种 IO 构造：人工中断（interrupt）与并行扇出（fanout）。

判据：
  1. (interrupt payload) 在 LangGraph 里真的暂停，恢复时拿到用户的值；
  2. (fanout items fn) 并行执行且保持输入顺序；
  3. (fanout-safe items fn) 单项失败不拖垮整体；
  4. 节点体读状态不再被误报「只写不读」。
"""

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
  (:lisp {helpers})
  (:state :fields ((answer :type str) (items :type list) (doubled :type list) (report :type str)))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #f :linter-check #f :test-runner "")
            (:correct :max-retries 1 :on-failure abort))
  (:workflow :entry {entry}
    :nodes ({nodes})
    :topology ((sequential ({order})))))
"""


def _compile(
    tmp_path: Path, nodes: str, order: str, entry: str, helpers: str = ""
) -> tuple[object, str]:
    src = BASE.format(nodes=nodes, order=order, entry=entry, helpers=helpers)
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
    spec = importlib.util.spec_from_file_location("io_demo_" + tmp_path.name, out)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, cp.stderr


def test_interrupt_pauses_and_resumes(tmp_path: Path) -> None:
    nodes = """(ask :type computation
                 :body (hash "answer" (interrupt (hash "node" "ask" "q" "批不批？")))
                 :output-fields (answer))"""
    mod, _ = _compile(tmp_path, nodes=nodes, order="ask", entry="ask")
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    from runtime.langgraph_bridge import build_graph

    h = mod.DemoHarness()
    app = build_graph(
        h.WORKFLOW, handlers={}, state_fields=h.STATE_FIELDS, checkpointer=MemorySaver()
    )
    cfg = {"configurable": {"thread_id": "t-int"}}

    paused = app.invoke({}, cfg)
    assert paused.get("__interrupt__"), "必须真的暂停"
    assert paused["__interrupt__"][0].value == {"node": "ask", "q": "批不批？"}

    done = app.invoke(Command(resume="approve"), cfg)
    assert done["answer"] == "approve"


def test_fanout_runs_in_order(tmp_path: Path) -> None:
    helpers = "(define (double x) (* x 2))"
    nodes = """(prepare :type computation :body (hash "items" (list 1 2 3 4)) :output-fields (items))
             (work :type computation
                   :body (hash "doubled" (fanout (hash-ref state "items") double))
                   :output-fields (doubled))"""
    mod, _ = _compile(tmp_path, nodes=nodes, order="prepare work", entry="prepare", helpers=helpers)
    from runtime.langgraph_bridge import build_graph

    h = mod.DemoHarness()
    out = build_graph(h.WORKFLOW, handlers={}, state_fields=h.STATE_FIELDS).invoke({})
    assert out["doubled"] == [2, 4, 6, 8]


def test_fanout_safe_isolates_failures(tmp_path: Path) -> None:
    helpers = "(define (inverse x) (/ 10 x))"
    nodes = """(prepare :type computation :body (hash "items" (list 1 0 5)) :output-fields (items))
             (work :type computation
                   :body (hash "report" (fanout-safe (hash-ref state "items") inverse))
                   :output-fields (report))"""
    mod, _ = _compile(tmp_path, nodes=nodes, order="prepare work", entry="prepare", helpers=helpers)
    from runtime.langgraph_bridge import build_graph

    h = mod.DemoHarness()
    out = build_graph(h.WORKFLOW, handlers={}, state_fields=h.STATE_FIELDS).invoke({})
    report = out["report"]
    assert [r["ok"] for r in report] == [True, False, True]
    assert "ZeroDivisionError" in report[1]["error"]
    assert report[0]["value"] == 10


def test_body_reads_are_not_reported_as_write_only(tmp_path: Path) -> None:
    """节点体读了 items，就不该再报「items 只写不读」。"""
    nodes = """(prepare :type computation :body (hash "items" (list 1 2)) :output-fields (items))
             (work :type computation
                   :body (hash "doubled" (map (lambda (x) x) (hash-ref state "items")))
                   :output-fields (doubled))"""
    _, stderr = _compile(tmp_path, nodes=nodes, order="prepare work", entry="prepare")
    assert "items 只写不读" not in stderr, stderr
    assert "doubled 只写不读" in stderr, "真·只写不读仍要提醒"
