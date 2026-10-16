"""US-08 / US-10：节点级插值与字段可达性（F-AMS-5 / F-AMS-3）。

判据（US-08）：{field} 只允许在 :dynamic；未知字段编译期拒。
判据（US-10）：读未声明字段 -> rc=1；只写不读 -> 警告；读无写且无默认 -> rc=1。
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

GOOD = """(:state :fields ((metrics :type dict :default ()) (stage :type str :default "")))
  (:workflow
    :entry plan
    :nodes ((plan :type agent
                  :prompt (:static "你是规划器。" :dynamic "当前指标：{metrics}")
                  :output-fields (stage))))"""


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


def test_prompt_segments_and_outputs_emitted(tmp_path: Path) -> None:
    cp = _compile(tmp_path, GOOD)
    assert cp.returncode == 0, cp.stderr[-500:]
    src = (tmp_path / "o.py").read_text(encoding="utf-8")
    ast.parse(src)
    m = re.search(r"self\.WORKFLOW: Dict\[str, Any\] = (.+)", src)
    assert m
    wf = ast.literal_eval(m.group(1))
    node = wf["nodes"][0]
    assert node["static"] == "你是规划器。"
    assert node["dynamic"] == "当前指标：{metrics}"
    assert node["output_fields"] == ["stage"]


def test_static_interpolation_fails(tmp_path: Path) -> None:
    cp = _compile(tmp_path, GOOD.replace("你是规划器。", "你是规划器。{stage}"))
    assert cp.returncode != 0
    assert ":static" in cp.stderr


def test_unknown_field_in_dynamic_fails(tmp_path: Path) -> None:
    cp = _compile(tmp_path, GOOD.replace("{metrics}", "{ghost}"))
    assert cp.returncode != 0
    assert "未声明字段" in cp.stderr


def test_write_only_field_warns(tmp_path: Path) -> None:
    cp = _compile(
        tmp_path,
        """(:state :fields ((stage :type str :default "")))
  (:workflow :entry plan
    :nodes ((plan :type agent :output-fields (stage))))""",
    )
    assert cp.returncode == 0, cp.stderr[-400:]
    assert "只写不读" in (cp.stderr + cp.stdout)


def test_read_without_writer_or_default_fails(tmp_path: Path) -> None:
    cp = _compile(
        tmp_path,
        """(:state :fields ((metrics :type dict)))
  (:workflow :entry plan
    :nodes ((plan :type agent
                  :prompt (:static "s" :dynamic "{metrics}"))))""",
    )
    assert cp.returncode != 0
    assert "无人写" in cp.stderr
