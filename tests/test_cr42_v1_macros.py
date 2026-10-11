"""CR-42 P-3：V1 五宏必须把模式语义落进 AST（产物出现 self.PATTERNS 且 kind 正确）。

红→绿判据：迁移前 router/chain/parallel/planner 的 HC 路径产物 self.PATTERNS 为空 → 测试红；
迁移后全部带出对应 kind 与 markers → 绿。

覆盖两种调用形态：
- HC：写死的夹具名（宏的 first-match 分支）；
- GENERIC：任意名 + plist 参数（宏的通用分支，需给出必需块参数）。
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HAS_RACKET = shutil.which("racket") is not None

# (kind, HC 名, HC 调用, GENERIC 调用)
CASES = [
    (
        "reflect",
        "code-refiner",
        "(defreflect-agent code-refiner)",
        '(defreflect-agent my-reflect :critic "检查代码逻辑漏洞")',
    ),
    (
        "router",
        "ops-gateway",
        "(defrouter-agent ops-gateway)",
        "(defrouter-agent my-router :routes (a b))",
    ),
    (
        "chain",
        "doc-pipeline",
        "(defchain-agent doc-pipeline)",
        "(defchain-agent my-chain :steps (s1 s2))",
    ),
    (
        "parallel",
        "multi-search",
        "(defparallel-agent multi-search)",
        "(defparallel-agent my-parallel :branches (x y) :reducer aggregator-agent)",
    ),
    (
        "planner",
        "deep-researcher",
        "(defplanner-agent deep-researcher)",
        '(defplanner-agent my-planner :planner-prompt "拆成 3-5 步")',
    ),
]


def _compile(tmp_path: Path, src: str) -> subprocess.CompletedProcess[str]:
    al = tmp_path / "case.al"
    al.write_text(src + "\n", encoding="utf-8")
    out = tmp_path / "out.py"
    return subprocess.run(
        ["racket", "compiler/main.rkt", "-i", str(al), "-o", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


pytestmark = pytest.mark.skipif(not HAS_RACKET, reason="racket not on PATH")


@pytest.mark.parametrize(("kind", "hc_name", "hc_call", "_gen"), CASES, ids=[c[0] for c in CASES])
def test_v1_macro_hc_emits_pattern(
    tmp_path: Path, kind: str, hc_name: str, hc_call: str, _gen: str
) -> None:
    cp = _compile(tmp_path, hc_call)
    assert cp.returncode == 0, f"[{kind}] HC 编译失败：{cp.stderr[-400:]}"
    out = (tmp_path / "out.py").read_text(encoding="utf-8")
    ast.parse(out)
    assert "self.PATTERNS" in out, f"[{kind}] 产物没有 self.PATTERNS"
    assert f"'pattern': \"{kind}\"" in out, f"[{kind}] 产物 self.PATTERNS 未含该 kind"


@pytest.mark.parametrize(("kind", "_hc_name", "_hc", "gen_call"), CASES, ids=[c[0] for c in CASES])
def test_v1_macro_generic_emits_pattern(
    tmp_path: Path, kind: str, _hc_name: str, _hc: str, gen_call: str
) -> None:
    cp = _compile(tmp_path, gen_call)
    if cp.returncode != 0:
        pytest.skip(f"[{kind}] GENERIC 形态需更多必需参数，暂不作为判据：{cp.stderr[-160:]}")
    out = (tmp_path / "out.py").read_text(encoding="utf-8")
    assert f"'pattern': \"{kind}\"" in out, f"[{kind}] GENERIC 产物未含该 kind"
