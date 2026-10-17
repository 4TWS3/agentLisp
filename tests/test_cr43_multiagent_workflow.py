"""US-06（D2 内聚）：defmultiagent 与等价显式 :workflow 产物一致（结构同构）。"""

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

EXPLICIT = """(define-agent team
  (:model :provider "anthropic" :name "m" :system-prompt "s")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #t)
            (:correct :max-retries 2 :on-failure abort))
  (:workflow :entry w1
    :nodes ((w1 :type subagent :isolation scoped :effect revertible)
            (w2 :type subagent :isolation scoped :effect revertible)
            (w3 :type subagent :isolation scoped :effect revertible))
    :topology ((edge w1 w2) (edge w1 w3))))
"""


def _wf(tmp_path: Path, src: str, name: str) -> dict:
    (tmp_path / (name + ".al")).write_text(src, encoding="utf-8")
    assert RACKET is not None
    cp = subprocess.run(
        [
            RACKET,
            str(MAIN),
            "-i",
            str(tmp_path / (name + ".al")),
            "-o",
            str(tmp_path / (name + ".py")),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr[-500:]
    text = (tmp_path / (name + ".py")).read_text(encoding="utf-8")
    ast.parse(text)
    m = re.search(r"self\.WORKFLOW: Dict\[str, Any\] = (.+)", text)
    assert m, "产物缺 WORKFLOW"
    return ast.literal_eval(m.group(1))


def test_defmultiagent_equals_explicit_workflow(tmp_path: Path) -> None:
    a = _wf(tmp_path, "(defmultiagent team orchestration w1 w2 w3)\n", "a")
    b = _wf(tmp_path, EXPLICIT, "b")
    assert a["entry"] == b["entry"] == "w1"
    assert a["nodes"] == b["nodes"], "节点表不一致"
    assert all(n["type"] == "subagent" for n in a["nodes"])
    assert all(n["isolation"] == "scoped" for n in a["nodes"])
    assert {(e["from"], e["to"]) for e in a["edges"]} == {
        (e["from"], e["to"]) for e in b["edges"]
    }, "边集合不一致"


def test_all_four_topologies_lower(tmp_path: Path) -> None:
    for topo in ("peer", "orchestration", "decentralised", "judge-driven"):
        wf = _wf(tmp_path, "(defmultiagent team " + topo + " w1 w2 w3)\n", topo)
        assert len(wf["nodes"]) == 3
        assert wf["edges"], "每个拓扑都应有边"
