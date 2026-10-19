"""「查得到、错得起」的机器保障。

- 查得到：docs/llm/al_catalog.json 必须与编译器一致（漂移即失败）
- 错得起：docs/llm/errors.json 的每条规则都带 原因 / 怎么改 / 例子，且能被真实报错命中
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "gen_al_catalog.py"
CATALOG = ROOT / "docs" / "llm" / "al_catalog.json"
ERRORS = ROOT / "docs" / "llm" / "errors.json"
MAIN = ROOT / "compiler" / "main.rkt"
_BUNDLED = ROOT / ".racket" / "bin" / "racket"
RACKET = "racket" if shutil.which("racket") else (str(_BUNDLED) if _BUNDLED.exists() else None)


def test_catalog_matches_compiler() -> None:
    """目录从编译器生成。新增形式却没更新目录 -> 这里失败。"""
    cp = subprocess.run(
        [sys.executable, str(GEN), "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
    )
    assert cp.returncode == 0, cp.stderr


def test_catalog_covers_every_block_and_node_type() -> None:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    for block in (":model", ":context", ":tools", ":harness", ":state", ":workflow", ":lisp"):
        assert block in data["blocks"], block
    assert data["enums"]["workflow_node_type"] == ["agent", "computation", "evaluator", "subagent"]
    assert data["enums"]["state_reducer"] == ["merge", "append", "sum"]
    assert data["lisp_core"], "核心函数表不能为空"


def test_every_error_hint_is_complete() -> None:
    data = json.loads(ERRORS.read_text(encoding="utf-8"))
    assert data["hints"], "至少要有一条"
    for h in data["hints"]:
        for key in ("match", "cause", "fix", "example"):
            assert h.get(key), f"缺 {key}：{h}"


def test_error_hint_shows_up_in_real_compile() -> None:
    """真实报错必须带出「原因 / 怎么改 / 例子」。"""
    if not RACKET:
        pytest.skip("racket 不可用")
    import tempfile

    src = """(define-agent bad
  (:model :provider "openai" :name "m" :system-prompt "s")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #f))
  (:state :fields ((a :type str)))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #f :linter-check #f :test-runner "")
            (:correct :max-retries 1 :on-failure abort))
  (:workflow :entry x
    :nodes ((x :type computation :body (hash "b" 1) :output-fields (b)))
    :topology ()))
"""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bad.al"
        p.write_text(src, encoding="utf-8")
        cp = subprocess.run(
            [RACKET, str(MAIN), "-i", str(p), "-o", str(Path(d) / "bad.py")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
            timeout=180,
        )
    assert cp.returncode != 0
    assert "原因:" in cp.stderr
    assert "怎么改:" in cp.stderr
    assert "例子:" in cp.stderr
