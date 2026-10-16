"""US-37：版本号单一真源一致性（v2.3.1）。

pyproject.toml / runtime.__version__ / host gateway / compiler CLI 必须同一版本。
防「升了一处漏三处」。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# (?<!_)：排除 schema_version 之类的非包版本字段
PAT = re.compile(r'(?<!_)version"?[ \t]*[:=][ \t]*"([^"]+)"')


def _pkg() -> str:
    from runtime import __version__

    return __version__


def test_pyproject_matches_runtime() -> None:
    src = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version = "([^"]+)"', src, re.M)
    assert m, "pyproject 缺 version"
    assert m.group(1) == _pkg(), "pyproject 与 runtime.__version__ 不一致"


def test_host_gateways_match_runtime() -> None:
    for rel in ("host/gateway.py", "host/gateway_sse.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        found = PAT.findall(src)
        assert found, rel + " 未找到 version"
        for v in found:
            assert v == _pkg(), rel + " 的 version " + v + " 与 runtime 不一致"


def test_compiler_cli_prints_runtime_version() -> None:
    src = (ROOT / "compiler" / "main.rkt").read_text(encoding="utf-8")
    assert "agentlispc " + _pkg() in src, "compiler/main.rkt 的版本串与 runtime 不一致"
