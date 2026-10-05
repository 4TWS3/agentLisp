"""AgentLisp v2.0 Roadmap Traceability Compliance Checker (stdlib zero-deps).

ISO/IEC/IEEE 29148 §8.3 验证完备性的路线图合规核查。每 CR 启动前自动运行，
消除 Reviewer 手工 heredoc Python 脚本的 80 行复制粘贴成本。

三类核查（失败 exit=1，stderr 前缀严格三选一，成功 stdout 空 exit=0）：
  1. FR-2  34-ID 三集合全等：孤儿 L315 = 附录 B 首列 = 正文词边界命中
  2. FR-3  基线整数五向全等：L274 = AC2_scn = AC2_pas = actual [ = --strict-baseline ]
  3. FR-4  32 行非汇总 Scenario==Passed：行数 32±1 warn，ScnSum≠PasSum 才 fail

CI 调用（ci.yml python-tests ubuntu 门禁）：
  uv run python scripts/check_roadmap_traceability.py \\
      --srs docs/spec/agentlisp_srs.md \\
      --pytest-junitxml junit/test-results.xml
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRS_DEFAULT = REPO_ROOT / "docs" / "spec" / "agentlisp_srs.md"

ID_RE_STR = (
    r"(AC-[123]|FR-(?:PARSER-[1-6]|CHECK-[0123]|CORRECT-1|MAGT-1|MEM-1|RUN-[1-4])|"
    r"NFR-(?:OBS-1|PERF-1a|PERF-1b|PERF-2|REL-[12]|SEC-1[a-c])|"
    r"IF-(?:API-1|CLI-1|MCP-1|SDK-1|TEMPORAL-1))"
)
ID_RE = re.compile(r"\b" + ID_RE_STR + r"\b")
APPB_ID_LINE_RE = re.compile(r"^\|\s*(?:\*\*?" + ID_RE_STR + r"\*\*?|" + ID_RE_STR + r")\s*\|")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="AgentLisp Roadmap Traceability Compliance Checker (O2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--srs",
        type=pathlib.Path,
        default=SRS_DEFAULT,
        help="SRS.md 路径（默认 docs/spec/agentlisp_srs.md）",
    )
    p.add_argument(
        "--pytest-junitxml",
        type=pathlib.Path,
        default=None,
        help="pytest junitxml 路径（优先读 tests 属性；缺失则 fallback 子进程跑 pytest）",
    )
    p.add_argument(
        "--strict-baseline",
        type=int,
        default=None,
        help="强制预期 pytest passed=N（五向全等；缺失则四向全等用 SRS L274）",
    )
    return p.parse_args()


def _read_srs(srs_path: pathlib.Path) -> str:
    if not srs_path.exists():
        print(f"ROADMAP-BASELINE-MISMATCH: SRS not found: {srs_path}", file=sys.stderr)
        sys.exit(1)
    return srs_path.read_text(encoding="utf-8")


def _extract_orphan_ids(srs: str) -> set[str]:
    m = re.search(r"### 孤儿需求核查[\s\S]*?\n(AC-1.*?IF-TEMPORAL-1)。", srs)
    if not m:
        return set()
    line = m.group(1)
    ids = {x.strip() for x in line.split(",") if x.strip()}
    ids.discard("NFR-PERF-1")
    return ids


def _extract_app_b_ids(srs: str) -> set[str]:
    ids: set[str] = set()
    app_b = srs.split("## 附录 B", 1)[1].split("## 附录 C", 1)[0]
    for line in app_b.splitlines():
        m = APPB_ID_LINE_RE.match(line.strip())
        if not m:
            continue
        found = m.group(1) or m.group(2)
        if found:
            ids.add(found)
    ids.discard("NFR-PERF-1")
    return ids


def _extract_body_ids(srs: str) -> set[str]:
    body = srs.split("## 附录 B")[0]
    ids = set(ID_RE.findall(body))
    ids.discard("NFR-PERF-1")
    return ids


def check_34id(srs: str, stderr_list: list[str]) -> None:
    orphan = _extract_orphan_ids(srs)
    appb = _extract_app_b_ids(srs)
    body = _extract_body_ids(srs)
    if orphan == appb == body and len(orphan) == 34:
        return
    stderr_list.append(
        "ROADMAP-ID-MISMATCH: "
        f"set(orphan-AppB)={sorted(orphan - appb)} "
        f"set(AppB-orphan)={sorted(appb - orphan)} "
        f"set(orphan-body)={sorted(orphan - body)} "
        f"set(body-orphan)={sorted(body - orphan)} "
        f"union={len(orphan | appb | body)}"
    )


def _extract_int(pattern: str, text: str, default: int | None = None) -> int | None:
    m = re.search(pattern, text)
    if not m:
        return default
    try:
        return int(m.group(1))
    except (ValueError, IndexError):
        return default


def _parse_pytest_from_junitxml(path: pathlib.Path) -> int | None:
    try:
        tree = ET.parse(path)
    except (ET.ParseError, FileNotFoundError, PermissionError):
        return None
    total = 0
    for ts in tree.getroot().iter("testsuite"):
        try:
            total += int(ts.attrib.get("tests", 0) or 0)
        except (ValueError, TypeError):
            pass
    return total or None


def _parse_pytest_fallback_subprocess() -> int | None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["AGENTLISP_DOCKER_INFRA"] = "true"
    try:
        cp = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--no-header",
                "-p",
                "no:cacheprovider",
                "runtime/tests",
                "scripts/tests",
                "host/tests",
            ],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=900,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    tail = (cp.stdout or "").splitlines()[-5:]
    for line in reversed(tail):
        m = re.search(r"(\d+) passed", line)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return None
    return None


def check_baseline(srs: str, args: argparse.Namespace, stderr_list: list[str]) -> None:
    app_b = srs.split("## 附录 B", 1)[1].split("## 附录 C", 1)[0]
    v1 = _extract_int(r"pytest (\d+) passed", srs)
    v2: int | None = None
    v3: int | None = None
    for line in app_b.splitlines():
        if line.strip().startswith("| **AC-2** |"):
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cols) >= 4:
                try:
                    v2 = int(re.sub(r"[^\d]", "", cols[1]) or "0")
                except ValueError:
                    v2 = None
                try:
                    v3 = int(re.sub(r"[^\d]", "", cols[2]) or "0")
                except ValueError:
                    v3 = None
            break
    v4: int | None = None
    if args.pytest_junitxml and args.pytest_junitxml.exists():
        v4 = _parse_pytest_from_junitxml(args.pytest_junitxml)
    if v4 is None:
        v4 = _parse_pytest_fallback_subprocess()
    v5 = args.strict_baseline
    values = [v1, v2, v3, v4]
    labels = ["L274", "AC2_scn", "AC2_pas", "actual"]
    if v5 is not None:
        values.append(v5)
        labels.append("strict")
    non_none = [(labels[i], v) for i, v in enumerate(values) if v is not None]
    if len(non_none) < 2:
        return
    uniq = {v for _, v in non_none}
    if len(uniq) == 1:
        return
    parts = " ".join(f"{k}={v}" for k, v in non_none)
    stderr_list.append(f"ROADMAP-BASELINE-MISMATCH: {parts} union_size={len(uniq)}")


def check_32rows_scn_eq_pas(srs: str, stderr_list: list[str]) -> None:
    app_b = srs.split("## 附录 B", 1)[1].split("## 附录 C", 1)[0]
    lines = app_b.splitlines()
    scn_sum = 0
    pas_sum = 0
    rows = 0
    for line in lines:
        s = line.strip()
        if not s.startswith("|") or s.startswith("| ---") or s.startswith("| 需求 ID"):
            continue
        if "| **AC-2** |" in s:
            continue
        if not APPB_ID_LINE_RE.match(s):
            continue
        cols = [c.strip() for c in s.strip("|").split("|")]
        if len(cols) < 4:
            continue
        try:
            scn = int(re.sub(r"[^\d]", "", cols[1]) or "0")
        except ValueError:
            scn = 0
        try:
            pas = int(re.sub(r"[^\d]", "", cols[2]) or "0")
        except ValueError:
            pas = 0
        rows += 1
        scn_sum += scn
        pas_sum += pas
    row_diff = abs(rows - 32)
    if scn_sum != pas_sum:
        stderr_list.append(
            "ROADMAP-SCENARIO-SUM-MISMATCH: "
            f"rows={rows}? ScnSum={scn_sum} PasSum={pas_sum} "
            f"expect_PasSum==ScnSum (fail_on_diff=true)"
        )
        return
    if row_diff > 1:
        print(
            f"[warn O2] rows={rows} not 32 (diff={row_diff}, allowed ±1); "
            f"ScnSum={scn_sum} PasSum={pas_sum}; only warn, not fail",
            file=sys.stderr,
        )


def main() -> int:
    args = _parse_args()
    srs = _read_srs(args.srs)
    stderr_list: list[str] = []
    check_34id(srs, stderr_list)
    check_baseline(srs, args, stderr_list)
    check_32rows_scn_eq_pas(srs, stderr_list)
    if stderr_list:
        for line in stderr_list:
            print(line, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
