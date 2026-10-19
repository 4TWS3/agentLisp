import atexit
import pathlib
import re
import subprocess
import sys
import tempfile

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_roadmap_traceability.py"
SRS_MD = REPO_ROOT / "docs" / "spec" / "agentlisp_srs.md"
with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as FAKE_JUNIT:
    FAKE_JUNIT.write(
        '<?xml version="1.0"?>'
        '<testsuites><testsuite tests="158" failures="0" errors="0" skipped="3">'
        '<testcase classname="m" name="x"/></testsuite></testsuites>'
    )
    FAKE_JUNIT_NAME = FAKE_JUNIT.name
atexit.register(lambda: pathlib.Path(FAKE_JUNIT_NAME).unlink(missing_ok=True))


def _run_cli(
    srs_md: pathlib.Path,
    extra: list[str] | None = None,
) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--srs",
        str(srs_md),
        "--pytest-junitxml",
        FAKE_JUNIT_NAME,
    ]
    if extra:
        cmd.extend(extra)
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT)
    )


def test_check_roadmap_traceability_legal_scenario_exit_zero_and_stdout_empty():
    cp = _run_cli(SRS_MD)
    assert cp.returncode == 0, f"stderr: {cp.stderr}"
    assert cp.stdout == ""
    assert not re.search(r"^ROADMAP-", cp.stderr, re.M)


def test_appendix_b_row_baseline_is_declarative():
    """附录 B 行数基线从 SRS 读，不再写死 32（2026-10-18 升级到 47）。"""
    content = SRS_MD.read_text(encoding="utf-8")
    assert "APPB_ROWS_BASELINE: 47" in content, "SRS 必须声明行数基线"
    cp = _run_cli(SRS_MD)
    assert cp.returncode == 0, cp.stderr
    assert "rows=" not in cp.stderr, f"当前行数与基线一致，不该告警：{cp.stderr}"


def test_appendix_b_row_drift_warns_but_does_not_fail():
    content = SRS_MD.read_text(encoding="utf-8")
    drifted = content.replace("APPB_ROWS_BASELINE: 47", "APPB_ROWS_BASELINE: 40", 1)
    assert drifted != content
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(drifted)
        tmp_srs = pathlib.Path(tmp.name)
    try:
        cp = _run_cli(tmp_srs)
    finally:
        tmp_srs.unlink(missing_ok=True)
    assert cp.returncode == 0, "行数漂移只告警，不失败"
    assert "rows=47" in cp.stderr and "APPB_ROWS_BASELINE=40" in cp.stderr


def test_check_roadmap_traceability_id_drift_exit_one_and_prefix_count_one():
    content = SRS_MD.read_text(encoding="utf-8")
    drifted = content.replace(
        "FR-PARSER-1, FR-PARSER-2, FR-PARSER-3",
        "FR-PARSER-1, FAKE-ID-999, FR-PARSER-2, FR-PARSER-3",
        1,
    )
    assert drifted != content
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(drifted)
        tmp_srs = pathlib.Path(tmp.name)
    try:
        cp = _run_cli(tmp_srs, extra=["--strict-baseline", "158"])
        assert cp.returncode == 1, f"stderr: {cp.stderr}"
        id_count = len(re.findall(r"^ROADMAP-ID-MISMATCH:", cp.stderr, re.M))
        base_count = len(re.findall(r"^ROADMAP-BASELINE-MISMATCH:", cp.stderr, re.M))
        assert id_count == 1
        assert base_count == 0
    finally:
        tmp_srs.unlink(missing_ok=True)


def test_check_roadmap_traceability_baseline_mismatch_exit_one_and_prefix_count_one():
    content = SRS_MD.read_text(encoding="utf-8")
    # CR-41 起 declared 基线来自 CR41_BASELINE_PASSED_COUNT。脚本只判 actual < declared，
    # 因此「下调声明值」天然安全、抓不出来；必须用「上调声明的基线」来验证脚本真的会拦。
    drifted = content.replace(
        "CR41_BASELINE_PASSED_COUNT: 146", "CR41_BASELINE_PASSED_COUNT: 999", 1
    ).replace("| **AC-2** | 146 | 146 |", "| **AC-2** | 999 | 999 |", 1)
    assert drifted != content
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(drifted)
        tmp_srs = pathlib.Path(tmp.name)
    try:
        cp = _run_cli(tmp_srs)
        assert cp.returncode == 1, f"stderr: {cp.stderr}"
        id_count = len(re.findall(r"^ROADMAP-ID-MISMATCH:", cp.stderr, re.M))
        base_count = len(re.findall(r"^ROADMAP-BASELINE-MISMATCH:", cp.stderr, re.M))
        assert base_count == 1
        assert id_count == 0
    finally:
        tmp_srs.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v", "-p", "no:cacheprovider", "--strict-markers"]))
