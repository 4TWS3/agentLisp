#!/usr/bin/env python3
"""US-42 口径核对：README / LANDED 注释 / 落地清单三处数字必须一致。

唯一真源：runtime/patterns/__init__.py 的 CONTRACTED / LANDED / DECLARED_ONLY。
三处文本必须逐字含同一口径短语：`契约 N / 落地 M / 声明层 K`。
（US-30 换口径：旧短语「落地 21 / 引擎消费 13 / 仅声明 8」见 US-42 handoff。）

退出码：0 = 三处一致；1 = 有不一致。
"""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    # Windows 默认 cp1252：脚本里有中文，不重设会 UnicodeEncodeError（CI 实测）
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.patterns import CONTRACTED, DECLARED_ONLY, LANDED  # noqa: E402

TARGETS = [
    ("README.md", ROOT / "README.md"),
    ("LANDED 注释", ROOT / "runtime" / "patterns" / "__init__.py"),
    ("落地清单", ROOT / "docs" / "spec" / "agentlisp_pattern_landing.md"),
]


def canonical_phrase() -> str:
    return f"契约 {len(CONTRACTED)} / 落地 {len(LANDED)} / 声明层 {len(DECLARED_ONLY)}"


def check() -> list[str]:
    problems: list[str] = []
    if DECLARED_ONLY & LANDED or (LANDED | DECLARED_ONLY) != CONTRACTED:
        problems.append("LANDED / DECLARED_ONLY 不构成 CONTRACTED 的划分")
    want = canonical_phrase()
    for label, path in TARGETS:
        if not path.is_file():
            problems.append(f"{label}：文件不存在 {path}")
            continue
        if want not in path.read_text(encoding="utf-8"):
            problems.append(f"{label}：缺口径短语 {want!r}")
    return problems


def main() -> int:
    problems = check()
    if problems:
        for p in problems:
            print("FAIL", p)
        return 1
    print(f"OK 三处口径一致：{canonical_phrase()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
