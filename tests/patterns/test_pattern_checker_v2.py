"""CR-41 V2 Pattern Macros · TDD 红断言（30 cases — 10 宏 × 3 场景 HC/GENERIC/REVERSE）
绑定 SRS 附录 B CR41-PAT01..10 Scn=Pas=3 each → 30 cases 对齐。

阶段 1 红：patterns_v2.rkt 10 宏 define-syntax TODO 占位 raise-syntax-error
→ 30 条全部 FAIL（pytest 30 failed）= TDD 红阶段证据
阶段 2 绿（T8..T17 10 宏实现后 → pytest 30/30 passed。
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPILER_DIR = PROJECT_ROOT / "compiler"
FIXTURES_V2_DIR = PROJECT_ROOT / "tests" / "patterns" / "fixtures_v2"
RACKET_BIN = "racket"
HAS_RACKET = shutil.which(RACKET_BIN) is not None

V2_MACROS = (
    "priority01",
    "decomp02",
    "fsm03",
    "eval04",
    "topic05",
    "decom06",
    "guard07",
    "hitl08",
    "exc09",
    "explore10",
)
SCENES = ("HC", "GENERIC", "REVERSE")

# 30 = 10 宏 × 3 场景
CASE_IDS = [f"{m}_{s}" for m in V2_MACROS for s in SCENES]
AL_FILES = {cid: FIXTURES_V2_DIR / f"{cid}.al" for cid in CASE_IDS}
EXPECTED_FILES = {cid: FIXTURES_V2_DIR / f"{cid}.expected.rkt" for cid in CASE_IDS}

# 与 V1 口径一致：无 Racket 环境则全部 skipif 等待 CI Ubuntu 提供红证据
pytestmark = pytest.mark.skipif(
    not HAS_RACKET,
    reason="Racket binary `racket` not found on PATH (请在 CI Ubuntu runner 跑 patterns_v2 测试；本机无 Racket 跳过，红证据见 _tmp_o13_patterns_mvp_verify.yml job 中 Racket 8.12 10 宏 TODO 将 FAIL)",
)


def _racket_macroexpand_v2(al_path: pathlib.Path) -> tuple[int, str, str]:
    """复用 V1 口径的 main.rkt --dump-ast，已在 expand-pattern-macros 合并命名空间
    (V1 + V2 双 require)
    """
    cmd = [
        RACKET_BIN,
        str(COMPILER_DIR / "main.rkt"),
        "--dump-ast",
        str(al_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    return proc.returncode, proc.stdout, proc.stderr


def _normalize_sexp(sexp_str: str) -> str:
    import re

    lines = []
    for line in sexp_str.splitlines():
        if line.lstrip().startswith(";"):
            continue
        lines.append(line)
    merged = "\n".join(lines)
    return re.sub(r"\s+", " ", merged).strip()


# ----------------------------------------------------------------------------
# V2-RED-01..30  10 宏 × 3 场景 = 30 cases（TDD 红：exit != 0 或 stdout 空
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", CASE_IDS, ids=CASE_IDS)
def test_v2_macro_expand_returns_valid_define_agent(case_id: str):
    """CR41-PAT 对应附录 B 的 Scn=Pas=3；红阶段 patterns_v2.rkt TODO 占位未实现
    → 宏展开必 FAIL；绿阶段实现后必须 (define-agent ...)
    """
    al = AL_FILES[case_id]
    exp = EXPECTED_FILES[case_id]
    assert al.exists(), f"missing fixture .al: {al}"
    assert exp.exists(), f"missing fixture .expected.rkt: {exp}"
    rc, out, err = _racket_macroexpand_v2(al)
    # 红阶段：define-syntax raise-syntax-error TODO → rc != 0 或 stderr 含 TODO
    # 绿阶段：rc == 0 + stdout 顶层 (define-agent ...)
    assert rc == 0, f"红阶段TODO占位未实现 rc={rc} stderr tail[-500:]= {err[-500:]}"
    assert out.strip(), "empty stdout (expected (define-agent ...) s-exp"
    nout = _normalize_sexp(out)
    assert nout.startswith("(define-agent"), (
        f"宏展开顶层形状错误 (V2 宏 {case_id} out[:160]={nout[:160]!r})"
    )
    expected_src = _normalize_sexp(exp.read_text(encoding="utf-8"))
    # 字节级 SDD 200 前缀全等 SBE
    assert nout[:200] == expected_src[:200], (
        f"V2 宏展开 SDD 前缀 200 bytes 不相等（case {case_id}）\n"
        f"ACTUAL[:200]  : {nout[:200]!r}\n"
        f"EXPECT[:200]: {expected_src[:200]!r}"
    )
