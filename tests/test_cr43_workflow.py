"""US-05 / US-07 / US-09：(:workflow …) 工作流图与编译期校验（F-AMS-1/2）。

判据（US-05）：支持 4 类拓扑，产物含节点与边。
判据（US-07）：:handler 格式编译期校验。
判据（US-09）：引用不存在节点 / 双入口（不可达）/ 未声明环 -> rc=1。
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

BASE = """(define-agent wf
  (:model :provider "anthropic" :name "m" :system-prompt "s")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #t)
            (:correct :max-retries 2 :on-failure abort))
  {extra})
"""

GOOD = """(:workflow
    :entry plan
    :nodes ((plan  :type agent)
            (calc  :type computation :handler "m.f")
            (judge :type evaluator))
    :topology ((sequential (plan calc))
               (conditional-loop :nodes (calc judge) :while "<0.85" :max-rounds 3)))"""


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


def _workflow(src: str) -> dict:
    m = re.search(r"self\.WORKFLOW: Dict\[str, Any\] = (.+)", src)
    assert m, "产物缺 self.WORKFLOW"
    return ast.literal_eval(m.group(1))


def test_workflow_emits_nodes_and_edges(tmp_path: Path) -> None:
    cp = _compile(tmp_path, GOOD)
    assert cp.returncode == 0, cp.stderr[-500:]
    src = (tmp_path / "o.py").read_text(encoding="utf-8")
    ast.parse(src)
    wf = _workflow(src)
    assert wf["entry"] == "plan"
    assert [n["name"] for n in wf["nodes"]] == ["plan", "calc", "judge"]
    assert wf["nodes"][1]["handler"] == "m.f"
    assert {"from": "plan", "to": "calc", "kind": "sequential"} in wf["edges"]
    assert wf["loops"][0]["nodes"] == ["calc", "judge"]


def test_nonexistent_node_fails(tmp_path: Path) -> None:
    cp = _compile(
        tmp_path,
        """(:workflow :entry plan
             :nodes ((plan :type agent))
             :topology ((edge plan nope)))""",
    )
    assert cp.returncode != 0
    assert "不存在的节点" in cp.stderr


def test_entry_not_declared_fails(tmp_path: Path) -> None:
    cp = _compile(
        tmp_path,
        """(:workflow :entry ghost
             :nodes ((plan :type agent)))""",
    )
    assert cp.returncode != 0
    assert ":entry" in cp.stderr


def test_unreachable_node_fails(tmp_path: Path) -> None:
    """双入口：孤岛节点从入口不可达。"""
    cp = _compile(
        tmp_path,
        """(:workflow :entry plan
             :nodes ((plan :type agent) (island :type agent)))""",
    )
    assert cp.returncode != 0
    assert "不可达" in cp.stderr


def test_edge_can_target_end(tmp_path: Path) -> None:
    """END 是合法汇点：edge / conditional-edge 都可以指向它（复刻 tianxuan 时需要）。"""
    cp = _compile(
        tmp_path,
        """(:workflow :entry a
             :nodes ((a :type agent))
             :topology ((conditional-edge :from a :to END)))""",
    )
    assert cp.returncode == 0, cp.stderr
    assert "'to': \"END\"" in (tmp_path / "o.py").read_text(encoding="utf-8")


def test_conditional_edge_cycle_is_allowed_with_warning(tmp_path: Path) -> None:
    """条件边成环合法（作者显式声明了分支），只告警不失败。

    依据：spec-writer 的 5 个环全由条件边构成（draft↔review、gm_review↔gm_qa、
    revise→review、confirm_clarify 自环、create_missing_foundation→scan）。
    """
    cp = _compile(
        tmp_path,
        """(:workflow :entry a
             :nodes ((a :type agent) (b :type agent))
             :topology ((conditional-edge :from a :to b)
                        (conditional-edge :from b :to a)))""",
    )
    assert cp.returncode == 0, cp.stderr
    assert "条件边成环" in cp.stderr


def test_undeclared_cycle_fails(tmp_path: Path) -> None:
    cp = _compile(
        tmp_path,
        """(:workflow :entry plan
             :nodes ((plan :type agent) (a :type agent) (b :type agent))
             :topology ((sequential (plan a b)) (edge b plan)))""",
    )
    assert cp.returncode != 0
    assert "未声明环" in cp.stderr


def test_workflow_and_multiagent_are_mutually_exclusive(tmp_path: Path) -> None:
    cp = _compile(
        tmp_path,
        GOOD + "\n  (:multiagent :topology star :workers ())",
    )
    assert cp.returncode != 0
    assert "互斥" in cp.stderr


def test_computation_node_requires_handler(tmp_path: Path) -> None:
    cp = _compile(
        tmp_path,
        """(:workflow :entry calc :nodes ((calc :type computation)))""",
    )
    assert cp.returncode != 0
    assert ":handler" in cp.stderr


def test_bad_handler_format_fails(tmp_path: Path) -> None:
    cp = _compile(
        tmp_path,
        """(:workflow :entry calc
             :nodes ((calc :type computation :handler "nofunc")))""",
    )
    assert cp.returncode != 0
    assert "格式" in cp.stderr


def test_duplicate_workflow_block_fails(tmp_path: Path) -> None:
    cp = _compile(tmp_path, GOOD + "\n  " + GOOD)
    assert cp.returncode != 0
    assert ":workflow 块重复" in cp.stderr
