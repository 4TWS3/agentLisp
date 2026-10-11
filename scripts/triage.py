#!/usr/bin/env python3
"""失败取证聚合器（triage）。

用途：改动任何判据或代码**之前**，先把失败按同一根因聚合出来。
教训来源：docs/spec/agentlisp_lessons_ledger.md 坑 #14（先猜后验，连改 3 次都没修好）。

用法：
    python3 scripts/triage.py                      # 全量 pytest
    python3 scripts/triage.py tests/patterns -x    # 追加参数透传给 pytest

输出三段：
1. 失败签名聚合（同一根因只显示一次，附命中数与样例测试）；
2. NFR02 cell 聚合（cell=... 出现次数）与 checker FAILED cells 聚合；
3. 完整 FAILED 列表。
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter

CELL_RE = re.compile(r"cell=([a-z0-9-]+)\(([^)]*)\)")
CHECKER_CELL_RE = re.compile(r"([A-Za-z0-9_-]+-agent)\s*\[([^\]]+)\]")
FAILED_LINE_RE = re.compile(r"^FAILED\s+(\S+)(?:\s+-\s+(.*))?$")
E_LINE_RE = re.compile(r"^E\s+(.*)$")
# 取「信息量最大」的一行：优先异常名开头的那行（AssertionError: … / KeyError: …）
EXC_LINE_RE = re.compile(r"^(?:[A-Za-z_.]*(?:Error|Exception|Warning))\b")
BLOCK_HEADER_RE = re.compile(r"^_{5,}\s*(.*?)\s*_{5,}$")

_NORMALIZERS = (
    (re.compile(r"0x[0-9a-f]+"), "HEXADDR"),
    (re.compile(r"'(?:[^'\\]|\\.)*'"), "'X'"),
    (re.compile(r'"(?:[^"\\]|\\.)*"'), '"X"'),
    # 宏名与参数 id 是「同一根因的不同受害者」，必须抽象掉，否则聚合不起来
    (re.compile(r"[a-z0-9-]+-agent"), "NAME-agent"),
    (re.compile(r"\[[^\]]*\]"), "[ID]"),
    (re.compile(r"\d+"), "N"),
)


# 这些错误里，引号内的名字就是关键信息，不能匿名化（triage 自己的教训）
_KEEP_QUOTED = ("ModuleNotFoundError", "ImportError", "AttributeError", "FileNotFoundError")


def normalize(msg: str) -> str:
    """把一条报错信息归一化成签名：去掉地址、数字、具体字符串。

    例外：导入类错误的模块名、属性名要保留，否则聚合后看不到真正缺什么。
    """
    out = msg.strip()
    if any(k in out for k in _KEEP_QUOTED):
        out = re.sub(r"0x[0-9a-f]+", "HEXADDR", out)
        out = re.sub(r"[a-z0-9-]+-agent", "NAME-agent", out)
        return out[:160]
    for rx, repl in _NORMALIZERS:
        out = rx.sub(repl, out)
    return out[:160]


def parse_pytest_output(text: str) -> dict:
    """解析 pytest 输出。纯函数，便于单测。"""
    blocks: list[tuple[str, str]] = []  # (测试名, 最后一条 E 行)
    current = None
    last_e = None
    for line in text.splitlines():
        m = BLOCK_HEADER_RE.match(line)
        if m:
            if current and last_e:
                blocks.append((current, last_e))
            current, last_e = m.group(1), None
            continue
        m = E_LINE_RE.match(line)
        if m and current:
            msg = m.group(1).strip()
            if last_e is None or EXC_LINE_RE.match(msg):
                # 首次记录，或遇到异常名开头的一行（更有信息量）则覆盖
                last_e = msg if EXC_LINE_RE.match(msg) or last_e is None else last_e
                if EXC_LINE_RE.match(msg):
                    last_e = msg

    if current and last_e:
        blocks.append((current, last_e))

    failed: list[tuple[str, str]] = []
    for line in text.splitlines():
        m = FAILED_LINE_RE.match(line)
        if m:
            failed.append((m.group(1), (m.group(2) or "").strip()))

    # 签名 → 命中数 + 样例
    sig_counter: Counter[str] = Counter()
    sig_examples: dict[str, str] = {}
    for name, msg in blocks:
        sig = normalize(msg)
        sig_counter[sig] += 1
        sig_examples.setdefault(sig, name)
    for nodeid, reason in failed:
        if not blocks:
            sig = normalize(reason or nodeid)
            sig_counter[sig] += 1
            sig_examples.setdefault(sig, nodeid)

    # cell 只从失败区块统计（summary 行会重复出现，避免双计）
    failure_region = text.split("short test summary info")[0]
    cells: Counter[str] = Counter()
    cell_labels: dict[str, str] = {}
    for m in CELL_RE.finditer(failure_region):
        cells[m.group(1)] += 1
        cell_labels.setdefault(m.group(1), m.group(2))

    checker_reasons: Counter[str] = Counter()
    for line in text.splitlines():
        if "FAILED cells:" not in line and "FAILED by-category:" not in line:
            continue
        for m in CHECKER_CELL_RE.finditer(line):
            checker_reasons[m.group(2)] += 1

    counts = _summary_counts(text)
    return {
        "counts": counts,
        "signatures": sig_counter,
        "examples": sig_examples,
        "cells": cells,
        "cell_labels": cell_labels,
        "checker_reasons": checker_reasons,
        "failed": failed,
    }


def _summary_counts(text: str) -> dict:
    m = re.search(r"(\d+) passed", text)
    passed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+) failed", text)
    failed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+) skipped", text)
    skipped = int(m.group(1)) if m else 0
    return {"passed": passed, "failed": failed, "skipped": skipped}


def render_report(rep: dict) -> str:
    c = rep["counts"]
    out = [f"结论：passed={c['passed']} failed={c['failed']} skipped={c['skipped']}"]
    if c["failed"] == 0:
        out.append("无失败，无需取证。")
        return "\n".join(out)

    out.append("")
    out.append("一、失败签名聚合（先看这里，同一签名命中多次 = 同一根因）")
    for sig, n in rep["signatures"].most_common():
        out.append(f"  [{n} 次] {sig}")
        out.append(f"         样例: {rep['examples'].get(sig, '?')}")

    if rep["cells"]:
        out.append("")
        out.append("二、NFR02 cell 聚合")
        for cell, n in rep["cells"].most_common():
            label = rep["cell_labels"].get(cell, "")
            out.append(f"  [{n} 次] {cell} ({label})")

    if rep["checker_reasons"]:
        out.append("")
        out.append("三、checker FAILED cells 聚合")
        for reason, n in rep["checker_reasons"].most_common():
            out.append(f"  [{n} 次] {reason}")

    out.append("")
    out.append("四、完整 FAILED 列表")
    for nodeid, reason in rep["failed"]:
        out.append(f"  {nodeid}" + (f"  |  {reason}" if reason else ""))

    out.append("")
    out.append("下一步：同一签名命中 >= 2 时，先修根因，再整体重跑；不要逐条改判据。")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    targets = [a for a in argv if not a.startswith("-")] or ["tests/"]
    extra = [a for a in argv if a.startswith("-")]
    cmd = [sys.executable, "-m", "pytest", *targets, "-q", "--no-cov", "-rf", "--tb=short", *extra]
    print("运行:", " ".join(cmd))
    cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    report = render_report(parse_pytest_output(cp.stdout + cp.stderr))
    print(report)
    return 0 if report.startswith("结论：passed=") and "failed=0" in report.splitlines()[0] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
