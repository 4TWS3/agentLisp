"""B-06：V1 五宏的 GENERIC 分支（非 HC 名）必须能编译。

修前三个缺陷：
  1. :model-name 没映射成 :name
  2. :tools 产成 (:tools :tools ...) 重复键
  3. 空 :context 缺 :memory-policy（且缺 :harness 直接报「缺少必需块」）

判据：每个宏只给最少参数，编译 rc=0，产物 PATTERNS 含正确 pattern 与参数。
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

CASES = [
    ('(defrouter-agent r1 :routes ("a=>b"))', "router", "routes", ["a=>b"]),
    ('(defchain-agent c1 :steps ("x" "y"))', "chain", "steps", ["x", "y"]),
    ('(defparallel-agent p1 :branches ("a" "b"))', "parallel", "branches", ["a", "b"]),
    ('(defplanner-agent pl1 :planner-prompt "拆解")', "planner", None, None),
]


def _compile(tmp: Path, src: str) -> str:
    (tmp / "x.al").write_text(src + "\n", encoding="utf-8")
    assert RACKET is not None
    cp = subprocess.run(
        [RACKET, str(MAIN), "-i", str(tmp / "x.al"), "-o", str(tmp / "x.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, (cp.stdout + cp.stderr)[-500:]
    return (tmp / "x.py").read_text(encoding="utf-8")


@pytest.mark.parametrize(("src", "kind", "key", "value"), CASES)
def test_generic_v1_macro_compiles(
    tmp_path: Path, src: str, kind: str, key: str, value: object
) -> None:
    text = _compile(tmp_path, src)
    ast.parse(text)
    m = re.search(r"self\.PATTERNS: List\[Dict\[str, Any\]\] = (.+)", text)
    assert m, "产物缺 PATTERNS"
    patterns = ast.literal_eval(m.group(1))
    assert patterns and patterns[0]["pattern"] == kind
    if key is not None:
        assert patterns[0][key] == value


def test_generic_macro_supplies_model_defaults(tmp_path: Path) -> None:
    """只给 :model-name 时，:provider 与 :system-prompt 必须被补齐（否则 PARSE_GENERIC 报缺字段）。"""
    text = _compile(tmp_path, '(defrouter-agent r2 :model-name "gpt-x" :routes ("a=>b"))')
    ast.parse(text)
    m = re.search(r"model_config: Dict\[str, Any\] = (\{.+?\})", text, re.S)
    assert m, "产物缺 model_config"
    cfg = ast.literal_eval(m.group(1))
    assert cfg["provider"] == "openai", "缺 :provider 时要有默认"
    assert cfg["name"] == "gpt-x", ":model-name 必须映射成 :name"
    assert cfg["system_prompt"], "缺 :system-prompt 时要有非空默认"
