"""行号映射：Python traceback -> .al 行号。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "al_traceback.py"

AL = """(define-agent demo
  (:model :provider "openai" :name "m" :system-prompt "s")
  (:state :fields ((x :type str)))
  (:workflow :entry first
    :nodes ((first :type computation :body (hash "x" 1) :output-fields (x))
            (second :type computation :body (hash "x" 2) :output-fields (x)))
    :topology ()))
"""

TB = """Traceback (most recent call last):
  File "/tmp/gen.py", line 42, in _al_node_second
    return _al.al_hash("x", 2)
NameError: name 'boom' is not defined
"""


def _run(tmp_path: Path, tb: str, al: str = AL) -> subprocess.CompletedProcess:
    al_p = tmp_path / "demo.al"
    al_p.write_text(al, encoding="utf-8")
    gen = tmp_path / "gen.py"
    gen.write_text("def _al_node_second(state):\n    return 2\n", encoding="utf-8")
    # traceback 里的路径必须是**真实产物路径**，否则帧会被当成外部文件过滤掉
    tb = tb.replace("/tmp/gen.py", str(gen))
    tb_p = tmp_path / "tb.txt"
    tb_p.write_text(tb, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(tb_p), str(gen), str(al_p)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
    )


def test_maps_node_frame_to_al_line(tmp_path: Path) -> None:
    cp = _run(tmp_path, TB)
    assert cp.returncode == 0, cp.stderr
    assert "节点 second" in cp.stdout
    assert "demo.al:6" in cp.stdout, cp.stdout  # second 在第 6 行


def test_tool_frame_is_recognized(tmp_path: Path) -> None:
    tb = TB.replace("_al_node_second", "_al_tool_switch_phase")
    cp = _run(tmp_path, tb)
    assert cp.returncode == 0
    assert "工具 switch_phase" in cp.stdout


def test_unrelated_frames_are_ignored(tmp_path: Path) -> None:
    tb = TB.replace("/tmp/gen.py", "/tmp/other.py")
    cp = _run(tmp_path, tb)
    assert cp.returncode == 1
    assert "没有来自生成文件的帧" in cp.stderr


def test_missing_declaration_is_reported_not_crashed(tmp_path: Path) -> None:
    tb = TB.replace("_al_node_second", "_al_node_ghost")
    cp = _run(tmp_path, tb)
    assert cp.returncode == 0
    assert "未找到声明" in cp.stdout
