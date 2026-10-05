from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
CHECKER_RKT: Path = REPO_ROOT / "compiler" / "checker.rkt"

RACKET_BIN: str | None = shutil.which("racket")

EXPECTED_SSOT_8: frozenset[str] = frozenset(
    {
        "bash",
        "git-push",
        "wget",
        "curl",
        "scp",
        "dd",
        "chmod",
        "sudo",
    }
)

RACKET_DEFINE_RE: re.Pattern[str] = re.compile(
    r"^\(define\s+SIDEEFFECT-BUILTIN-TOOLS\s+'\(([^)]*)\)\)\s*$"
)


@pytest.mark.req("FR-CHECK-2")
def test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal(
    tmp_path: Path,
) -> None:
    """FR-CHECK-2 SIDEEFFECT-BUILTIN-TOOLS 双端 SSOT 8 项 bitwise 全等。

    SSOT 枚举清单（顺序无关，集合全等）：
        bash, git-push, wget, curl, scp, dd, chmod, sudo

    制度化双路径 hard-assert 零 pytest.skip：
      * 路径 A（racket 在 PATH）：真 subprocess 绝对路径 require
        compiler/checker.rkt，displayln SIDEEFFECT-BUILTIN-TOOLS，抽 8
        token → 与 Python frozenset + EXPECTED_SSOT_8 三向全等。若
        returncode != 0 则回退到路径 B 继续硬断言（不是 skip）。
      * 路径 B fallback（racket 不在 PATH，或路径 A subprocess 失败）：
        静态 grep CHECKER_RKT L87 (define SIDEEFFECT-BUILTIN-TOOLS '(*))
        单行正则抽 8 token → 再三向集合全等。
    """

    from runtime.checker import SIDEEFFECT_BUILTIN_TOOLS

    python_set: set[str] = set(SIDEEFFECT_BUILTIN_TOOLS)
    expected_set: set[str] = set(EXPECTED_SSOT_8)

    scenario_tag: str = "ssot_8_items_bitwise_equal"
    assert scenario_tag in __name__ or scenario_tag in (
        test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal.__name__
    )

    racket_set: set[str]
    racket_from_source_ok: bool = False

    if RACKET_BIN is not None:
        script_src: Path = tmp_path / "print_sideeffect.rkt"
        script_src.write_text(
            f"""\
#lang racket/base
(require (file "{CHECKER_RKT.as_posix()}"))
(displayln SIDEEFFECT-BUILTIN-TOOLS)
""",
            encoding="utf-8",
        )

        proc: subprocess.CompletedProcess[str] = subprocess.run(
            [RACKET_BIN, str(script_src)],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "PLTADDONDIR": str(tmp_path / "racket-addons"),
            },
            check=False,
        )
        if proc.returncode == 0:
            tokens: list[str] = proc.stdout.strip().split()
            if len(tokens) == 8 and all(isinstance(t, str) and t for t in tokens):
                racket_set = set(tokens)
                racket_from_source_ok = True

    if not racket_from_source_ok:
        assert CHECKER_RKT.exists(), f"fallback 需要 Racket checker 源但不存在: {CHECKER_RKT}"
        rkt_text: str = CHECKER_RKT.read_text(encoding="utf-8")
        matched: re.Match[str] | None = None
        for line in rkt_text.splitlines():
            m: re.Match[str] | None = RACKET_DEFINE_RE.match(line)
            if m is not None:
                matched = m
                break
        assert matched is not None, (
            "fallback 正则未匹配到 (define SIDEEFFECT-BUILTIN-TOOLS '(*)) 行"
        )
        racket_tokens: list[str] = matched.group(1).split()
        assert len(racket_tokens) == 8, (
            f"fallback 抽取 token 数 = {len(racket_tokens)} 期望 8；tokens={racket_tokens}"
        )
        racket_set = set(racket_tokens)

    assert len(racket_set) == 8, (
        f"racket_set len={len(racket_set)} 期望 8；items={sorted(racket_set)}"
    )
    assert len(python_set) == 8, (
        f"python_set len={len(python_set)} 期望 8；items={sorted(python_set)}"
    )
    assert len(expected_set) == 8

    diff_racket_vs_expected: set[str] = racket_set.symmetric_difference(expected_set)
    diff_python_vs_expected: set[str] = python_set.symmetric_difference(expected_set)
    diff_racket_vs_python: set[str] = racket_set.symmetric_difference(python_set)
    assert racket_set == expected_set == python_set, (
        "SSOT 8 项 sideeffect builtin 双端未 bitwise equal "
        f"（scenario={scenario_tag}）。\n"
        f"  EXPECTED 8 项基准 = {sorted(expected_set)}\n"
        f"  Racket 抽取 = {sorted(racket_set)}\n"
        f"  Python 抽取 = {sorted(python_set)}\n"
        f"  racket Δ expected = {sorted(diff_racket_vs_expected)}\n"
        f"  python Δ expected = {sorted(diff_python_vs_expected)}\n"
        f"  racket Δ python = {sorted(diff_racket_vs_python)}"
    )
    assert racket_set == python_set
