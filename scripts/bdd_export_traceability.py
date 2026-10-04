"""从 pytest --junitxml 导出的结果生成 SRS-ID → Scenario Traceability Matrix。

用法：
  python3 scripts/bdd_export_traceability.py --junitxml artifacts/results.xml \
      --output artifacts/traceability_matrix.md

生成的 Markdown 表格每行：
  | SRS-ID | Scenario 数 | Passed | Failed | Skipped/Xfail | 覆盖到的 Scenario 列表 |

设计目标：
  * SRS 29148 要求的「需求 → 测试 → 代码」可追溯性：
    SRS §5.2 每个需求要有唯一的 ID；§8.3 验证时要列出每个需求关联的测试用例
    及其结果。本脚本把 junitxml 中每个 testcase 的 <property name="req"> 值
    （由 conftest.py 的 autouse fixture 把 @pytest.mark.req 写入）作为
    聚合键，生成一份可人工审查的 Markdown 矩阵。
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import pathlib
import sys
import xml.etree.ElementTree as ET
from typing import Any


@dataclasses.dataclass
class _ScenarioResult:
    name: str
    classname: str
    passed: bool = False
    failed: bool = False
    skipped: bool = False
    xfailed: bool = False

    @property
    def status(self) -> str:
        if self.passed:
            return "passed"
        if self.failed:
            return "failed"
        if self.xfailed:
            return "xfailed"
        if self.skipped:
            return "skipped"
        return "unknown"


@dataclasses.dataclass
class _SRSBucket:
    srs_id: str
    scenarios: list[_ScenarioResult] = dataclasses.field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.scenarios)

    @property
    def passed_count(self) -> int:
        return sum(1 for s in self.scenarios if s.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for s in self.scenarios if s.failed)

    @property
    def skip_xfail_count(self) -> int:
        return sum(1 for s in self.scenarios if s.skipped or s.xfailed)

    def scenario_list(self, limit: int = 6) -> str:
        names = sorted({f"「{s.name}」" for s in self.scenarios})
        if len(names) <= limit:
            return "、".join(names)
        head = "、".join(names[:limit])
        return f"{head} 等 {len(names)} 个"


def _parse_junit(xml_path: pathlib.Path) -> list[tuple[_ScenarioResult, list[str], list[str]]]:
    """解析 junitxml，返回 (testcase_result, req_id_list, tag_list) 列表。"""
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    # pytest junitxml 顶层是 <testsuites><testsuite> 或直接 <testsuite>
    testcases: list[ET.Element] = []
    if root.tag == "testsuite":
        testcases = list(root.findall("testcase"))
    else:
        for ts in root.iter("testsuite"):
            testcases.extend(list(ts.findall("testcase")))
    rows: list[tuple[_ScenarioResult, list[str], list[str]]] = []
    for tc in testcases:
        name = tc.attrib.get("name", "")
        classname = tc.attrib.get("classname", "")
        res = _ScenarioResult(name=name, classname=classname)
        reqs: list[str] = []
        tags: list[str] = []
        # 结果判定：存在 <failure>/<error> → failed；<skipped> → skipped；
        # 若 skipped message 含 "xfail" → xfailed；否则 passed
        has_failure = (tc.find("failure") is not None) or (tc.find("error") is not None)
        skip_elem = tc.find("skipped")
        if has_failure:
            res.failed = True
        elif skip_elem is not None:
            msg = (skip_elem.attrib.get("message", "") + skip_elem.attrib.get("type", "")).lower()
            if "xfail" in msg or "expected failure" in msg:
                res.xfailed = True
            else:
                res.skipped = True
        else:
            res.passed = True
        # properties 解析
        for prop in tc.iter("property"):
            pname = prop.attrib.get("name", "")
            pvalue = prop.attrib.get("value", "")
            if pname == "req" and pvalue:
                reqs.append(pvalue)
            elif pname == "tag" and pvalue:
                tags.append(pvalue)
        rows.append((res, reqs, tags))
    return rows


def _aggregate(buckets: collections.defaultdict[str, _SRSBucket], rows: list[tuple[_ScenarioResult, list[str], list[str]]]) -> None:
    for scenario, reqs, _tags in rows:
        if reqs:
            for rid in reqs:
                buckets[rid].srs_id = rid
                buckets[rid].scenarios.append(scenario)
        else:
            buckets["__NO_SRS_ID__"].srs_id = "(未映射 SRS-ID)"
            buckets["__NO_SRS_ID__"].scenarios.append(scenario)


def _srs_id_sort_key(srs_id: str) -> tuple[Any, ...]:
    """SRS-ID 排序：AC-<n> < FR-<NAME>-<n> < NFR-<NAME>-<n> < IF-<NAME>-n < R-n < 其它。"""
    order = {"AC": 0, "FR": 1, "NFR": 2, "IF": 3, "R": 4}
    if srs_id == "__NO_SRS_ID__":
        return (99, srs_id)
    parts = srs_id.split("-", 2)
    prefix = parts[0] if parts else ""
    if prefix not in order:
        return (10, srs_id)
    try:
        suffix = parts[-1] if parts else "0"
        num = ""
        letter = ""
        for ch in suffix:
            if ch.isdigit():
                num += ch
            else:
                letter += ch
        num_int = int(num) if num else 0
        return (order[prefix], parts[1] if len(parts) >= 3 else "", num_int, letter)
    except Exception:
        return (order.get(prefix, 10), srs_id)


def generate_markdown(rows: list[tuple[_ScenarioResult, list[str], list[str]]]) -> str:
    buckets: collections.defaultdict[str, _SRSBucket] = collections.defaultdict(lambda: _SRSBucket(srs_id=""))
    _aggregate(buckets, rows)
    sorted_ids = sorted(buckets.keys(), key=_srs_id_sort_key)
    total_all = sum(b.total for b in buckets.values())
    passed_all = sum(b.passed_count for b in buckets.values())
    failed_all = sum(b.failed_count for b in buckets.values())
    skip_xfail_all = sum(b.skip_xfail_count for b in buckets.values())
    lines: list[str] = []
    lines.append("# AgentLisp v2.0 需求 ↔ 测试 可追溯性矩阵 (Traceability Matrix)")
    lines.append("")
    lines.append("> 生成来源：`pytest --junitxml` 导出结果 + `conftest.py` @req marker → property")
    lines.append("> ")
    lines.append(f"> 总计：{total_all} 个 Scenario，Passed={passed_all}，Failed={failed_all}，Skipped/Xfail={skip_xfail_all}")
    lines.append("")
    lines.append("| SRS-ID | Scenario 数量 | Passed | Failed | Skipped/Xfail | 覆盖到的 Scenario 列表 |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
    for srs_id in sorted_ids:
        b = buckets[srs_id]
        display_id = b.srs_id
        lines.append(
            f"| {display_id} | {b.total} | {b.passed_count} | {b.failed_count} | {b.skip_xfail_count} | {b.scenario_list()} |"
        )
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append("- `(未映射 SRS-ID)`：对应测试用例没有打上 @pytest.mark.req(...) / BDD feature 没有 @FR-CHECK-1 等 SRS tag。")
    lines.append("- 与 `docs/spec/agentlisp_srs.md` 附录 B 的 Traceability Matrix 做交叉比对，即可判定「需求覆盖完备性」。")
    lines.append("- Failed ≠ 0 的需求行：需要修复对应测试用例后再发版。")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="从 junitxml 生成 SRS Traceability Markdown Matrix")
    ap.add_argument("--junitxml", required=True, type=pathlib.Path, help="pytest --junitxml 生成的 XML 路径")
    ap.add_argument("--output", required=True, type=pathlib.Path, help="输出 Markdown 文件路径")
    args = ap.parse_args(argv)
    if not args.junitxml.exists():
        print(f"[ERROR] junitxml not found: {args.junitxml}", file=sys.stderr)
        return 2
    rows = _parse_junit(args.junitxml)
    md = generate_markdown(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    unique_reqs: set[str] = set()
    for _sc, reqs, _tags in rows:
        for r in reqs:
            unique_reqs.add(r)
    print(f"[OK] Traceability matrix written to: {args.output}")
    print(f"     SRS-ID count: {len(unique_reqs)}; total testcases: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
