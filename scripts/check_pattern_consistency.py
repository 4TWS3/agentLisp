#!/usr/bin/env python3
"""US-42 口径核对：README / LANDED 注释 / 落地清单三处数字必须一致。

唯一真源：runtime/patterns/__init__.py 的 LANDED / DECLARED_ONLY / ENGINE_CONSUMED。
三处文本必须逐字含同一口径短语：`落地 N / 引擎消费 M / 仅声明 K`。

退出码：0 = 三处一致；1 = 有不一致。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.patterns import DECLARED_ONLY, ENGINE_CONSUMED, LANDED  # noqa: E402

TARGETS = [
    ("README.md", ROOT / "README.md"),
    ("LANDED 注释", ROOT / "runtime" / "patterns" / "__init__.py"),
    ("落地清单", ROOT / "docs" / "spec" / "agentlisp_pattern_landing.md"),
]


def canonical_phrase() -> str:
    return f"落地 {len(LANDED)} / 引擎消费 {len(ENGINE_CONSUMED)} / 仅声明 {len(DECLARED_ONLY)}"


def check() -> list[str]:
    problems: list[str] = []
    if not DECLARED_ONLY <= LANDED:
        problems.append(f"DECLARED_ONLY 含未落地 kind：{sorted(DECLARED_ONLY - LANDED)}")
    if ENGINE_CONSUMED != LANDED - DECLARED_ONLY:
        problems.append("ENGINE_CONSUMED != LANDED - DECLARED_ONLY")
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
