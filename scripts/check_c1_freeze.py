#!/usr/bin/env python3
"""US-39 / P2-7：C1 冻结文件追认核对。

读 docs/spec/c1_freeze_ratification.md 的追认表，重算每个文件的 sha256。
不符 = 未追认的改动 -> rc=1。

退出码：0 = 全部追认一致；1 = 有未追认改动或格式不符。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "spec" / "c1_freeze_ratification.md"
HEX = "0123456789abcdef"


def _rows(text: str) -> list[tuple[str, str]]:
    """从 markdown 表里取 (路径, sha256)。只认第 2 列是 64 位 hex 的行。"""
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2 and len(cells[1]) == 64 and all(c in HEX for c in cells[1]):
            rows.append((cells[0], cells[1]))
    return rows


def check() -> list[str]:
    if not DOC.is_file():
        return ["缺追认表 " + str(DOC)]
    rows = _rows(DOC.read_text(encoding="utf-8"))
    if not rows:
        return ["追认表为空或格式不符（需要 | 路径 | sha256 | ... |）"]
    problems: list[str] = []
    for rel, want in rows:
        path = ROOT / rel
        if not path.is_file():
            problems.append("C1 文件缺失：" + rel)
            continue
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != want:
            problems.append(
                "未追认的改动："
                + rel
                + "（记录 "
                + want[:8]
                + "，实际 "
                + got[:8]
                + "）→ 更新追认表"
            )
    return problems


def main() -> int:
    problems = check()
    if problems:
        for p in problems:
            print("FAIL", p)
        return 1
    print("OK C1 追认表一致：" + str(len(_rows(DOC.read_text(encoding="utf-8")))) + " 个文件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
