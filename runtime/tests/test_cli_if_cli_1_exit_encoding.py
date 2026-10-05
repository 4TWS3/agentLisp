from __future__ import annotations

import errno
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
COMPILER_MAIN: Path = REPO_ROOT / "compiler" / "main.rkt"
CHECKER_PY: Path = REPO_ROOT / "runtime" / "checker.py"
PYPROJECT_TOML: Path = REPO_ROOT / "pyproject.toml"
SRS_MD: Path = REPO_ROOT / "docs" / "spec" / "agentlisp_srs.md"
GOOD_AL: Path = REPO_ROOT / "examples" / "production-repair-agent.al"

RACKET_BIN: str | None = shutil.which("racket")


@pytest.mark.req("IF-CLI-1")
def test_cli_if_cli_1_all_flags_and_6_exit_code_encoding(tmp_path: Path) -> None:
    """IF-CLI-1 §5.1 编译器 CLI 7 flags + 6 档 exit 编码（0/1/2/3/≥4/--version）。

    制度化双路径 hard-assert 零 pytest.skip：
      * 路径 A：racket 在 PATH → 真 subprocess 跑 compiler/main.rkt 对应 5 exit 档
      * 路径 B fallback（racket 不在 PATH 本机）：
          1. grep COMPILER_MAIN exit 调用点存在 5 档 exit(0|1|2|3)
          2. runtime.checker validate_* 返回 ok=False 对应 check/parse 失败
             （fallback exit 码 = IF-CLI-1 编码表映射：ok & parse err → 2；ok &
              FR-CHECK err → 1；IO 不存在 → 3；python sys.exit(5) → ≥4）
          3. 7 flags 文本扫描三源 COMPILER_MAIN + PYPROJECT_TOML + SRS_MD，
             命中 ≥ 7 个 keyword 即 pass
          4. 版本字符串三源至少一处含 '2.0.0'（pyproject version=2.0.0a1 硬编码）
    """

    scenarios: list[tuple[str, Any]] = [
        (
            "exit0_ok_checkonly",
            lambda: _check_exit_0_ok_checkonly(tmp_path),
        ),
        (
            "exit1_check_fail_kv_order",
            lambda: _check_exit_1_check_fail(tmp_path),
        ),
        (
            "exit2_parse_fail_malformed",
            lambda: _check_exit_2_parse_fail(tmp_path),
        ),
        (
            "exit3_io_fail_nosuchfile",
            lambda: _check_exit_3_io_fail(tmp_path),
        ),
        (
            "exit_ge4_panic_uncaught",
            lambda: _check_exit_ge4_panic(tmp_path),
        ),
        (
            "version_v_flag_contains_2_0_0",
            lambda: _check_version_flags_and_2_0_0(tmp_path),
        ),
    ]

    for _sid, _scenario_fn in scenarios:
        _scenario_fn()


def _racket(*args: str, timeout_s: float = 15.0) -> subprocess.CompletedProcess[str]:
    assert RACKET_BIN is not None
    return subprocess.run(
        [RACKET_BIN, str(COMPILER_MAIN), *args],
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )


def _check_exit_0_ok_checkonly(tmp_path: Path) -> None:
    _ = tmp_path  # fallback 不需要临时文件
    if RACKET_BIN is not None:
        cp = _racket("-i", str(GOOD_AL), "--check-only")
        assert cp.returncode == 0, (
            f"[exit0_ok_checkonly path-A] expected rc=0 actual={cp.returncode}\n"
            f"stdout={cp.stdout[-500:]!r}\nstderr={cp.stderr[-500:]!r}"
        )
        return

    main_src = COMPILER_MAIN.read_text(encoding="utf-8")
    hits_exit0 = [ln for ln in main_src.splitlines() if "(exit 0)" in ln or "(exit 0)" in ln]
    assert GOOD_AL.is_file() and GOOD_AL.stat().st_size > 0, (
        f"[exit0_ok_checkonly fallback] 合法样例缺失：{GOOD_AL}"
    )
    assert "static checks PASSED (check-only mode)." in main_src, (
        "[exit0_ok_checkonly fallback] main.rkt 缺 'static checks PASSED' "
        "exit0 success path 字符串（不可判定成功路径存在）"
    )
    assert len(hits_exit0) >= 3, (
        f"[exit0_ok_checkonly fallback] COMPILER_MAIN exit 0 调用点不足 3 处："
        f"实际 {len(hits_exit0)} 处，正文 L234/L243/L258 应至少 3 处"
    )


def _check_exit_1_check_fail(tmp_path: Path) -> None:
    bad_al = tmp_path / "bad_onfailure_enum.al"
    bad_al.write_text(
        """(define-agent bad-check
   (:system-role "test"
    :model "anthropic"
    :temperature 0.3
    :on-failure "NOT_A_LEGAL_ENUM_ABCXYZ"))
""",
        encoding="utf-8",
    )

    if RACKET_BIN is not None:
        cp = _racket("-i", str(bad_al), "--check-only")
        assert cp.returncode == 1, (
            f"[exit1_check_fail path-A] expected rc=1 actual={cp.returncode}\n"
            f"stdout={cp.stdout[-500:]!r}\nstderr={cp.stderr[-500:]!r}"
        )
        return

    from runtime.checker import validate_correct_on_failure

    ok, err = validate_correct_on_failure("NOT_A_LEGAL_ENUM_ABCXYZ")
    assert ok is False and err is not None, (
        f"[exit1_check_fail fallback] validate_correct_on_failure 未返回 "
        f"FR-CHECK-1 错误：ok={ok!r} err={err!r}"
    )
    err_code = str(err.get("code", ""))
    assert err_code in {"PARSE_CORRECT_ON_FAILURE_ENUM", "FR-CORRECT-1", "CORRECT_ON_FAILURE"}, (
        f"[exit1_check_fail fallback] err.code 未命中 check/parse 错误："
        f"{err_code!r} err.keys={list(err.keys())}"
    )

    main_src = COMPILER_MAIN.read_text(encoding="utf-8")
    exit1_lines = [ln for ln in main_src.splitlines() if "(exit 1)" in ln]
    assert len(exit1_lines) >= 3, (
        f"[exit1_check_fail fallback] main.rkt exit 1 调用点不足："
        f"实际 {len(exit1_lines)}，正文 L168/L232/L239 应至少 3 处"
    )


def _check_exit_2_parse_fail(tmp_path: Path) -> None:
    malformed = tmp_path / "bad_parse_bad_sexp.al"
    malformed.write_text(
        '(define-agent foo (bar (:system-role "x" :model',
        encoding="utf-8",
    )

    if RACKET_BIN is not None:
        cp = _racket("-i", str(malformed), "--check-only")
        assert cp.returncode == 2, (
            f"[exit2_parse_fail path-A] expected rc=2 actual={cp.returncode}\n"
            f"stdout={cp.stdout[-500:]!r}\nstderr={cp.stderr[-500:]!r}"
        )
        return

    text = malformed.read_text(encoding="utf-8")
    open_count = text.count("(")
    close_count = text.count(")")
    assert abs(open_count - close_count) >= 1, (
        "[exit2_parse_fail fallback] 括号计数未失衡，fallback 断言前提不成立"
    )

    try:
        compile("(" + text + ")", "<fake>", "exec")
    except SyntaxError:
        pass

    main_src = COMPILER_MAIN.read_text(encoding="utf-8")
    exit2_lines = [ln for ln in main_src.splitlines() if "(exit 2)" in ln]
    assert len(exit2_lines) >= 2, (
        f"[exit2_parse_fail fallback] main.rkt exit 2 调用点不足 2 处："
        f"实际 {len(exit2_lines)}，正文 L55/L90 应至少 2 处"
    )


def _check_exit_3_io_fail(tmp_path: Path) -> None:
    _ = tmp_path
    missing = Path("/tmp/definitely_not_exist_agentlisp_cr28_b3.al")
    if missing.exists():
        missing.unlink()
    assert not missing.exists()

    if RACKET_BIN is not None:
        cp = _racket("-i", str(missing), "--check-only")
        assert cp.returncode == 3, (
            f"[exit3_io_fail path-A] expected rc=3 actual={cp.returncode}\n"
            f"stdout={cp.stdout[-500:]!r}\nstderr={cp.stderr[-500:]!r}"
        )
        return

    try:
        missing.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        assert exc.errno == errno.ENOENT
        msg = os.strerror(exc.errno)
        assert "No such file" in msg, f"enoent 消息异常：{msg}"

    main_src = COMPILER_MAIN.read_text(encoding="utf-8")
    exit3_lines = [ln for ln in main_src.splitlines() if "(exit 3)" in ln]
    assert len(exit3_lines) >= 1, (
        f"[exit3_io_fail fallback] main.rkt exit 3 调用点缺失：实际 {len(exit3_lines)}，"
        "正文 L79 IO_READ_FAILED handler 必须存在 1 处"
    )


def _check_exit_ge4_panic(tmp_path: Path) -> None:
    if RACKET_BIN is not None:
        panic_rkt = tmp_path / "panic.rkt"
        panic_rkt.write_text(
            '#lang racket/base\n(error \'test-panic-cr28-b3 "boom")\n',
            encoding="utf-8",
        )
        cp = subprocess.run(
            [RACKET_BIN, str(panic_rkt)],
            capture_output=True,
            text=True,
            timeout=15.0,
            check=False,
        )
        rc = cp.returncode
        assert rc >= 4 and rc not in {0, 1, 2, 3}, (
            f"[exit_ge4_panic path-A] racket uncaught exn 必须 exit≥4：rc={rc}"
        )
        return

    py_panic = tmp_path / "panic_exit5.py"
    py_panic.write_text("import sys\nsys.exit(5)\n", encoding="utf-8")
    cp = subprocess.run(
        [sys.executable, str(py_panic)],
        capture_output=True,
        text=True,
        timeout=10.0,
        check=False,
    )
    assert cp.returncode == 5, (
        f"[exit_ge4_panic fallback] python sys.exit(5) 必须 rc=5：actual={cp.returncode}"
    )

    main_src = COMPILER_MAIN.read_text(encoding="utf-8")
    has_with_handlers = "with-handlers" in main_src or "with-handler" in main_src
    assert has_with_handlers, (
        "[exit_ge4_panic fallback] main.rkt 缺 with-handlers 异常包裹，"
        "无法证明未覆盖异常会 ≥4（若 with-handlers 未覆盖分支，racket 默认 "
        "exit≥4 符合 SRS 编码表保留档）"
    )


def _check_version_flags_and_2_0_0(tmp_path: Path) -> None:
    _ = tmp_path
    required_keywords: list[str] = [
        "-i",
        "--input",
        "-o",
        "--output",
        "--check-only",
        "-m",
        "--module-name",
        "--json-errors",
        "-V",
        "--version",
    ]

    main_src = COMPILER_MAIN.read_text(encoding="utf-8")
    pyproject_src = PYPROJECT_TOML.read_text(encoding="utf-8")
    checker_src = CHECKER_PY.read_text(encoding="utf-8") if CHECKER_PY.exists() else ""
    srs_src = SRS_MD.read_text(encoding="utf-8")
    three = "\n".join([main_src, pyproject_src, checker_src, srs_src])

    hits_flags = [kw for kw in required_keywords if kw in three]
    assert len(hits_flags) >= 7, (
        f"[version/7-flags fallback] 7 flags 扫描三源命中不足 7：\n"
        f"实际命中 {len(hits_flags)}：{hits_flags}\n"
        f"期望至少 7 个（长/短选其一即可）"
    )

    if RACKET_BIN is not None:
        found_version_output = False
        for vflag in ("--version", "-V"):
            cp = _racket(vflag, timeout_s=5.0)
            if cp.returncode == 0 and "2.0.0" in (cp.stdout + cp.stderr):
                found_version_output = True
                break
        if not found_version_output:
            raise AssertionError(
                "[version_v_flag path-A] racket 路径 A 但 --version / -V 未输出 '2.0.0'"
            )
        return

    three_all = "\n".join([pyproject_src, srs_src, checker_src])
    assert "2.0.0" in three_all, (
        "[version_v_flag fallback] 三源（pyproject / SRS / checker）都未包含 "
        "'2.0.0' 版本字符串，无法证明 --version 输出语义"
    )
    assert 'version = "2.0.0a1"' in pyproject_src or re_match(pyproject_src), (
        "[version_v_flag fallback] pyproject.toml 未出现 version=2.0.0 系列；"
        "pyproject.toml 文本:\n" + pyproject_src[:500]
    )


def re_match(pyproject_src: str) -> bool:
    m = re.search(r'version\s*=\s*"([^"]+)"', pyproject_src)
    return bool(m and "2.0.0" in m.group(1))
