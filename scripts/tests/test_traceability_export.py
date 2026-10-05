import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "bdd_export_traceability.py"
FALLBACK_JSON = REPO_ROOT / "scripts" / "tests" / "traceability_manifest_fallback.json"
SRS_MD = REPO_ROOT / "docs" / "spec" / "agentlisp_srs.md"
EXPECTED_HEADER = (
    "| 需求 ID | Scenario 数 | Passed | Failed | Skip/Xfail | "
    "pytest / RackUnit 代表性用例 ID | 代码锚（精确文件:行范围） |"
)
EXPECTED_SEP = "| --- | ---: | ---: | ---: | ---: | --- | --- |"


def _run_cli(
    junitxml_bytes: bytes, output_md: pathlib.Path, extra: list[str] | None = None
) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile("wb", suffix=".xml", delete=False) as jf:
        jf.write(junitxml_bytes)
        junit_path = jf.name
    try:
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--junitxml",
            junit_path,
            "--output",
            str(output_md),
        ]
        if extra:
            cmd.extend(extra)
        return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    finally:
        pathlib.Path(junit_path).unlink(missing_ok=True)


def test_traceability_header_matches_appendix_b_and_digit_columns_right_aligned(tmp_path):
    """A-3 smoke 1：列头 7 列逐字全等附录 B，数字列分隔线全部右对齐 ---:"""
    output = tmp_path / "tr.md"
    cp = _run_cli(
        b'<?xml version="1.0"?><testsuites><testsuite name="t"><testcase classname="m" name="x"/></testsuite></testsuites>',
        output,
        extra=["--fallback-manifest", str(FALLBACK_JSON), "--drift-against", "/tmp/nonexistent.md"],
    )
    assert cp.returncode == 0, f"stderr: {cp.stderr}"
    lines = output.read_text(encoding="utf-8").splitlines()
    header_idx = next(i for i, line in enumerate(lines) if line.startswith("| 需求 ID"))
    assert lines[header_idx] == EXPECTED_HEADER
    assert lines[header_idx + 1] == EXPECTED_SEP


def test_traceability_srs_ids_are_unique_rows_and_coverage_ge_thirty(tmp_path):
    """A-3 smoke 2：SRS-ID 行唯一性 + fallback manifest 驱动 ≥30 条非空行。"""
    output = tmp_path / "tr.md"
    cp = _run_cli(
        b'<?xml version="1.0"?><testsuites><testsuite name="t"><testcase classname="m" name="x"/></testsuite></testsuites>',
        output,
        extra=["--fallback-manifest", str(FALLBACK_JSON), "--drift-against", "/tmp/nonexistent.md"],
    )
    assert cp.returncode == 0
    content = output.read_text(encoding="utf-8")
    ids = re.findall(r"^\|\s*\*\*((?:AC|FR|NFR|IF)-[A-Za-z0-9-]+)\*\*\s*\|", content, re.M)
    assert len(ids) >= 30, f"只抓到 {len(ids)} 条，fallback manifest 加载失败"
    assert len(ids) == len(set(ids)), f"存在重复 ID: {[i for i in ids if ids.count(i) > 1]}"


def test_traceability_drift_mode_exits_one_with_strict_stderr_prefixes(tmp_path):
    """A-3 smoke 3：drift 模式 exit=1，stderr 前缀严格 ORPHAN-DETECTED:/DRIFT:。"""
    xml = textwrap.dedent("""\
    <?xml version="1.0"?>
    <testsuites><testsuite name="t">
      <testcase classname="m" name="test_fr_parser_1_ok">
        <properties>
          <property name="req" value="FR-PARSER-1"/>
        </properties>
      </testcase>
      <testcase classname="m" name="test_extra_foo_99_drift">
        <properties>
          <property name="req" value="EXTRA-FOO-99"/>
        </properties>
      </testcase>
    </testsuite></testsuites>
    """).encode("utf-8")
    output = tmp_path / "tr.md"
    cp = _run_cli(
        xml,
        output,
        extra=["--drift-against", str(SRS_MD)],
    )
    assert cp.returncode == 1, f"期望 exit=1，实际={cp.returncode}，stderr={cp.stderr}"
    lines_stderr = cp.stderr.splitlines()
    assert any(line.startswith("ORPHAN-DETECTED:") for line in lines_stderr), (
        f"缺 ORPHAN-DETECTED 前缀，stderr={cp.stderr}"
    )
    assert any(line.startswith("DRIFT:") for line in lines_stderr), (
        f"缺 DRIFT 前缀，stderr={cp.stderr}"
    )
