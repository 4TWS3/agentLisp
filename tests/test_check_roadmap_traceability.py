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
        '<testsuites><testsuite tests="128" failures="0" errors="0" skipped="3">'
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
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))


def test_check_roadmap_traceability_legal_scenario_exit_zero_and_stdout_empty():
    cp = _run_cli(SRS_MD)
    assert cp.returncode == 0, f"stderr: {cp.stderr}"
    assert cp.stdout == ""
    assert not re.search(r"^ROADMAP-", cp.stderr, re.M)


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
        cp = _run_cli(tmp_srs, extra=["--strict-baseline", "128"])
        assert cp.returncode == 1, f"stderr: {cp.stderr}"
        id_count = len(re.findall(r"^ROADMAP-ID-MISMATCH:", cp.stderr, re.M))
        base_count = len(re.findall(r"^ROADMAP-BASELINE-MISMATCH:", cp.stderr, re.M))
        assert id_count == 1
        assert base_count == 0
    finally:
        tmp_srs.unlink(missing_ok=True)


def test_check_roadmap_traceability_baseline_mismatch_exit_one_and_prefix_count_one():
    content = SRS_MD.read_text(encoding="utf-8")
    drifted = content.replace("pytest 128 passed", "pytest 119 passed", 1).replace(
        "CR39_BASELINE_PASSED_COUNT: 128", "CR39_BASELINE_PASSED_COUNT: 119"
    )
    assert drifted != content
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(drifted)
        tmp_srs = pathlib.Path(tmp.name)
    try:
        cp = _run_cli(tmp_srs, extra=["--strict-baseline", "128"])
        assert cp.returncode == 1, f"stderr: {cp.stderr}"
        id_count = len(re.findall(r"^ROADMAP-ID-MISMATCH:", cp.stderr, re.M))
        base_count = len(re.findall(r"^ROADMAP-BASELINE-MISMATCH:", cp.stderr, re.M))
        assert base_count == 1
        assert id_count == 0
    finally:
        tmp_srs.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v", "-p", "no:cacheprovider", "--strict-markers"]))
