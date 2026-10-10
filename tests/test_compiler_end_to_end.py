"""P0 端到端编译闸门：.al → Racket CLI → Python 产物（真测试，非报告型）。

审计 finding：此前端到端编译只有「报告型」步骤（continue-on-error，恒绿），
没有任何测试校验编译产物能否通过 Python 语法校验。本文件把它变成阻塞型断言。

覆盖：
- 15 个正向夹具（V1 5 + V2 10）必须 exit=0、产物 ast.parse 通过、含 HARNESS_REGISTRY 与 class；
- 5 个 fr_pattern_02_*_auto_raise 负向夹具必须 exit != 0（SBE 契约：错误输入要显式失败）。
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RACKET_BIN = "racket"
MAIN = ROOT / "compiler" / "main.rkt"

HAS_RACKET = shutil.which(RACKET_BIN) is not None

V1_FIXTURES = ROOT / "tests" / "patterns" / "fixtures"
V2_FIXTURES = ROOT / "tests" / "patterns" / "fixtures_v2"

POSITIVE = (
    [
        (V1_FIXTURES / "defreflect_code_refiner.al", "v1-defreflect"),
        (V1_FIXTURES / "defrouter_ops_gateway.al", "v1-defrouter"),
        (V1_FIXTURES / "defchain_doc_pipeline.al", "v1-defchain"),
        (V1_FIXTURES / "defparallel_multi_search.al", "v1-defparallel"),
        (V1_FIXTURES / "defplanner_deep_researcher.al", "v1-defplanner"),
    ]
    + [(p, f"v2-{p.name}") for p in sorted(V2_FIXTURES.glob("*_hc_HC.al"))]
    + [
        (ROOT / "examples" / "repair_agent.al", "examples-repair_agent"),
    ]
)

NEGATIVE = sorted(V1_FIXTURES.glob("fr_pattern_02_*_auto_raise.al"))


def _compile(al: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [RACKET_BIN, str(MAIN.relative_to(ROOT)), "-i", str(al), "-o", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )


@pytest.mark.skipif(not HAS_RACKET, reason="racket not on PATH")
@pytest.mark.parametrize(("al", "name"), POSITIVE, ids=[n for _, n in POSITIVE])
def test_positive_fixture_compiles_to_valid_python(al: Path, name: str, tmp_path: Path) -> None:
    assert al.exists(), f"missing fixture {al}"
    out = tmp_path / "out.py"
    proc = _compile(al, out)
    assert proc.returncode == 0, f"[{name}] racket exit={proc.returncode}\n{proc.stderr[-600:]}"
    assert out.exists(), f"[{name}] 未产出文件"
    src = out.read_text(encoding="utf-8")
    ast.parse(src)  # 语法不合法直接失败
    assert "HARNESS_REGISTRY" in src, f"[{name}] 产物缺少 HARNESS_REGISTRY"
    assert "class " in src, f"[{name}] 产物缺少 harness 类"


@pytest.mark.skipif(not HAS_RACKET, reason="racket not on PATH")
@pytest.mark.parametrize("al", NEGATIVE, ids=[p.name for p in NEGATIVE])
def test_negative_fixture_is_rejected(al: Path, tmp_path: Path) -> None:
    proc = _compile(al, tmp_path / "out.py")
    assert proc.returncode != 0, f"[{al.name}] 错误输入本应失败，但编译成功"
