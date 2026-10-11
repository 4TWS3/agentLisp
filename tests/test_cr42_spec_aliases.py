"""规格 §3 BNF 别名宏：defprioritized-agent / defa2a-server / defresilient-agent /
defapproval-agent / defguarded-agent。

做法：取对应主宏的 HC 夹具输入，只把宏名换成别名，编译后断言：
- 退出码 0；
- 产物含与主宏相同的 (:pattern :kind …)。
这样别名与主宏的一致性有判据，而不是靠人工比对。
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "patterns" / "fixtures_v2"
HAS_RACKET = shutil.which("racket") is not None

# (别名, 主宏, 夹具 key, 期望 kind)
ALIASES = [
    ("defprioritized-agent", "defpriority-agent", "priority01", "priority"),
    ("defa2a-server", "defa2a-agent", "a2a16", "a2a"),
    ("defresilient-agent", "defexception-agent", "exc09", "exception"),
    ("defapproval-agent", "defhitl-agent", "hitl08", "hitl"),
    ("defguarded-agent", "defguardrails-safety-agent", "guard07", "guardrails-safety"),
]

pytestmark = pytest.mark.skipif(not HAS_RACKET, reason="racket not on PATH")


@pytest.mark.parametrize(
    ("alias", "canonical", "key", "kind"), ALIASES, ids=[a[0] for a in ALIASES]
)
def test_alias_compiles_like_canonical(
    tmp_path: Path, alias: str, canonical: str, key: str, kind: str
) -> None:
    src = (FIX / f"{key}_hc_HC.al").read_text(encoding="utf-8")
    assert canonical in src, f"夹具 {key} 未使用主宏 {canonical}"
    patched = src.replace(canonical, alias, 1)
    al = tmp_path / "c.al"
    al.write_text(patched, encoding="utf-8")
    cp = subprocess.run(
        ["racket", "compiler/main.rkt", "-i", str(al), "-o", str(tmp_path / "o.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert cp.returncode == 0, f"[{alias}] 编译失败：{cp.stderr[-300:]}"
    out = (tmp_path / "o.py").read_text(encoding="utf-8")
    ast.parse(out)
    assert f"'pattern': \"{kind}\"" in out, f"[{alias}] 产物未含 kind={kind}"


def test_alias_list_is_complete() -> None:
    """5 个别名都必须出现在 patterns_v2.rkt 与 main.rkt 白名单里。"""
    rkt = (ROOT / "compiler" / "patterns_v2.rkt").read_text(encoding="utf-8")
    main = (ROOT / "compiler" / "main.rkt").read_text(encoding="utf-8")
    for alias, *_ in ALIASES:
        assert re.search(rf"define-syntax \({alias} ", rkt), f"{alias} 未生成"
        assert alias in main, f"{alias} 未登记进 main.rkt 白名单"
