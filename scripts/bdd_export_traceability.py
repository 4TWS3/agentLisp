"""从 pytest --junitxml 导出结果生成 SRS-ID → Scenario Traceability Matrix。

严格对齐 docs/spec/agentlisp_srs.md 附录 B 7 列表头；支持 drift 模式校验
「附录 B 矩阵 vs 真实测试覆盖」的双向完备性；fallback manifest 兜底
pytest junit 不导出 @pytest.mark.req 标签时的静态覆盖声明。

CLI 调用（附录 B L314 写死，参数名不可改）：
  uv run python scripts/bdd_export_traceability.py \
      --junitxml junit/test-results.xml \
      --output artifacts/traceability_matrix.md

附加参数（drift / 兜底清单）：
  --drift-against FILE    默认 docs/spec/agentlisp_srs.md，解析其附录 B 矩阵
                          首列 ID 与真实聚合 ID 做差，发现 ORPHAN / DRIFT 时
                          exit=1 并 stderr 前缀严格 ORPHAN-DETECTED:/DRIFT:
  --req-tag STR           junitxml <property name="..."> 键名，默认 req
  --fallback-manifest FILE.json
                          静态 {SRS-ID: [[代表测试名, 代码锚], ...]} JSON，
                          pytest junit 未注入 @pytest.mark.req 时兜底使用
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import pathlib
import re
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
    fallback_pairs: list[tuple[str, str]] = dataclasses.field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.scenarios) if self.scenarios else len(self.fallback_pairs)

    @property
    def passed_count(self) -> int:
        if self.scenarios:
            return sum(1 for s in self.scenarios if s.passed)
        return len(self.fallback_pairs)

    @property
    def failed_count(self) -> int:
        return sum(1 for s in self.scenarios if s.failed)

    @property
    def skip_xfail_count(self) -> int:
        return sum(1 for s in self.scenarios if s.skipped or s.xfailed)

    def representative_tests(self, limit: int = 6) -> str:
        if self.scenarios:
            names = sorted({s.name for s in self.scenarios})
            if len(names) <= limit:
                return "、".join(f"`{n}`" for n in names)
            return "、".join(f"`{n}`" for n in names[:limit]) + f" 等 {len(names)} 个"
        if self.fallback_pairs:
            names = sorted({p[0] for p in self.fallback_pairs})
            return "、".join(f"`{n}`" for n in names[:limit]) + (
                f" 等 {len(names)} 个" if len(names) > limit else ""
            )
        return "-"

    def code_anchors(self) -> str:
        if self.fallback_pairs:
            anchors = sorted({p[1] for p in self.fallback_pairs if p[1]})
            if anchors:
                return "、".join(anchors)
        return "-"


def _parse_junit(xml_path: pathlib.Path, req_tag: str) -> list[tuple[_ScenarioResult, list[str]]]:
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    testcases: list[ET.Element] = []
    if root.tag == "testsuite":
        testcases = list(root.findall("testcase"))
    else:
        for ts in root.iter("testsuite"):
            testcases.extend(list(ts.findall("testcase")))
    rows: list[tuple[_ScenarioResult, list[str]]] = []
    for tc in testcases:
        name = tc.attrib.get("name", "")
        classname = tc.attrib.get("classname", "")
        res = _ScenarioResult(name=name, classname=classname)
        reqs: list[str] = []
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
        for prop in tc.iter("property"):
            pname = prop.attrib.get("name", "")
            pvalue = prop.attrib.get("value", "")
            if pname == req_tag and pvalue:
                reqs.append(pvalue)
        rows.append((res, reqs))
    return rows


def _load_fallback_manifest(path: pathlib.Path | None) -> dict[str, list[tuple[str, str]]]:
    if path is None or not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[tuple[str, str]]] = {}
    for srs_id, pairs in raw.items():
        clean: list[tuple[str, str]] = []
        for p in pairs or []:
            if isinstance(p, (list, tuple)) and len(p) >= 1:
                clean.append((str(p[0]), str(p[1]) if len(p) >= 2 else ""))
        out[srs_id] = clean
    return out


def _aggregate(
    buckets: collections.defaultdict[str, _SRSBucket],
    junit_rows: list[tuple[_ScenarioResult, list[str]]],
    manifest: dict[str, list[tuple[str, str]]],
) -> set[str]:
    all_ids: set[str] = set()
    for scenario, reqs in junit_rows:
        if reqs:
            for rid in reqs:
                buckets[rid].srs_id = rid
                buckets[rid].scenarios.append(scenario)
                all_ids.add(rid)
        else:
            buckets["__NO_SRS_ID__"].srs_id = "(未映射 SRS-ID)"
            buckets["__NO_SRS_ID__"].scenarios.append(scenario)
    for srs_id, pairs in manifest.items():
        all_ids.add(srs_id)
        if srs_id not in buckets:
            buckets[srs_id].srs_id = srs_id
        buckets[srs_id].fallback_pairs.extend(pairs)
    return all_ids


def _srs_id_sort_key(srs_id: str) -> tuple[Any, ...]:
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


ID_PAT = re.compile(r"^(AC|FR|NFR|IF)-[A-Za-z0-9-]+$")


def _parse_appendix_b_matrix_ids(spec_md: pathlib.Path) -> set[str]:
    if not spec_md.exists():
        return set()
    t = spec_md.read_text(encoding="utf-8")
    if "## 附录 B" not in t:
        return set()
    appendix_b = t.split("## 附录 B", 1)[1]
    matrix_block = appendix_b.split("### 孤儿需求核查", 1)[0]
    ids: set[str] = set()
    for line in matrix_block.split("\n"):
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cols:
            continue
        clean = cols[0].strip().strip("*").strip()
        if ID_PAT.match(clean):
            ids.add(clean)
    return ids


def generate_markdown(
    junit_rows: list[tuple[_ScenarioResult, list[str]]], manifest: dict[str, list[tuple[str, str]]]
) -> str:
    buckets: collections.defaultdict[str, _SRSBucket] = collections.defaultdict(
        lambda: _SRSBucket(srs_id="")
    )
    _aggregate(buckets, junit_rows, manifest)
    sorted_ids = sorted(buckets.keys(), key=_srs_id_sort_key)
    total_all = sum(b.total for b in buckets.values() if b.srs_id != "(未映射 SRS-ID)")
    passed_all = sum(b.passed_count for b in buckets.values())
    failed_all = sum(b.failed_count for b in buckets.values())
    skip_xfail_all = sum(b.skip_xfail_count for b in buckets.values())
    lines: list[str] = []
    lines.append("# AgentLisp v2.0 需求 ↔ 测试 ↔ 代码 可追溯性矩阵")
    lines.append("")
    lines.append("> 生成来源：`pytest --junitxml` 导出结果 + fallback-manifest 静态兜底")
    lines.append("> ")
    lines.append(
        f"> 总计：{total_all} 个 Scenario，Passed={passed_all}，Failed={failed_all}，Skip/Xfail={skip_xfail_all}"
    )
    lines.append("")
    # 7 列列头必须与 agentlisp_srs.md 附录 B 逐字全等
    lines.append(
        "| 需求 ID | Scenario 数 | Passed | Failed | Skip/Xfail | pytest / RackUnit 代表性用例 ID | 代码锚（精确文件:行范围） |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | --- | --- |")
    for srs_id in sorted_ids:
        b = buckets[srs_id]
        display_id = f"**{b.srs_id}**" if ID_PAT.match(b.srs_id) else b.srs_id
        lines.append(
            f"| {display_id} | {b.total} | {b.passed_count} | {b.failed_count} | {b.skip_xfail_count} | {b.representative_tests()} | {b.code_anchors()} |"
        )
    lines.append("")
    lines.append("## 说明")
    lines.append("")
    lines.append(
        "- `(未映射 SRS-ID)`：对应测试用例未打 @pytest.mark.req(...) 标签且 fallback-manifest 中无兜底条目。"
    )
    lines.append(
        "- 与 `docs/spec/agentlisp_srs.md` 附录 B 做 diff 即可判定「需求覆盖完备性 / 漂移」。"
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="从 junitxml + fallback manifest 生成 SRS Traceability Matrix"
    )
    ap.add_argument(
        "--junitxml", required=True, type=pathlib.Path, help="pytest --junitxml XML 路径"
    )
    ap.add_argument("--output", required=True, type=pathlib.Path, help="输出 Markdown 路径")
    ap.add_argument(
        "--drift-against",
        default=pathlib.Path("docs/spec/agentlisp_srs.md"),
        type=pathlib.Path,
        help="解析其附录 B 矩阵首列 ID 做完备性校验 (默认 docs/spec/agentlisp_srs.md)",
    )
    ap.add_argument("--req-tag", default="req", type=str, help="junitxml property 键名 (默认 req)")
    ap.add_argument(
        "--fallback-manifest",
        default=None,
        type=pathlib.Path,
        help="JSON: {SRS-ID: [[代表测试, 代码锚], ...]}，兜底 junit 未注入 req 的场景",
    )
    args = ap.parse_args(argv)
    if not args.junitxml.exists():
        print(f"[ERROR] junitxml not found: {args.junitxml}", file=sys.stderr)
        return 2
    junit_rows = _parse_junit(args.junitxml, args.req_tag)
    manifest = _load_fallback_manifest(args.fallback_manifest)
    md = generate_markdown(junit_rows, manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(md, encoding="utf-8")
    covered_ids: set[str] = set()
    for _sc, reqs in junit_rows:
        covered_ids.update(reqs)
    covered_ids.update(manifest.keys())
    if args.drift_against and args.drift_against.exists():
        matrix_ids = _parse_appendix_b_matrix_ids(args.drift_against)
        if matrix_ids:
            orphan = sorted(matrix_ids - covered_ids)
            drift = sorted(covered_ids - matrix_ids - {"__NO_SRS_ID__"})
            if orphan:
                print(
                    f"ORPHAN-DETECTED: {len(orphan)} 条 SRS-ID 在矩阵中但无任何测试覆盖:",
                    file=sys.stderr,
                )
                for rid in orphan:
                    print(f"ORPHAN-DETECTED:   - {rid}", file=sys.stderr)
            if drift:
                print(
                    f"DRIFT: {len(drift)} 条 SRS-ID 在测试中但未写入附录 B 矩阵:", file=sys.stderr
                )
                for rid in drift:
                    print(f"DRIFT:   - {rid}", file=sys.stderr)
            if orphan or drift:
                return 1
    print(f"[OK] Traceability matrix written to: {args.output}")
    print(
        f"     覆盖 SRS-ID 数量: {len(covered_ids - {'__NO_SRS_ID__'})}; 总 testcases: {len(junit_rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
