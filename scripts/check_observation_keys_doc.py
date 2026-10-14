#!/usr/bin/env python3
"""US-24 核对：runtime 真读的观察值键，必须在用户文档里有说明。

唯一真源 = 代码里的读取点（observation.get / observation[...]）。
文档不准漏键。多了没关系（文档可以先写）。

退出码：0 = 文档覆盖全部读取点；1 = 有漏。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "spec" / "agentlisp_observation_keys.md"
RUNTIME = ROOT / "runtime"

BT = chr(96)  # 反引号。用 chr 避开源码里的引号嵌套

# 代码读取点：observation.get("k") 或 observation["k"]
CODE_RE = re.compile(r"""observation(?:\.get\(\s*|\[\s*)["']([a-z_]+)["']""")
# 文档键表：某行以 | + 反引号 + key + 反引号 + | 开头
DOC_RE = re.compile(r"^\|\s*" + BT + r"([a-z_]+)" + BT + r"\s*\|", re.MULTILINE)


def code_keys() -> set[str]:
    keys: set[str] = set()
    for path in sorted(RUNTIME.rglob("*.py")):
        keys |= set(CODE_RE.findall(path.read_text(encoding="utf-8")))
    return keys


def doc_keys() -> set[str]:
    return set(DOC_RE.findall(DOC.read_text(encoding="utf-8")))


def check() -> list[str]:
    if not DOC.is_file():
        return ["缺文档 " + str(DOC)]
    missing = sorted(code_keys() - doc_keys())
    if missing:
        return ["文档缺这些观察值键：" + str(missing) + "（代码在读，用户看不到说明）"]
    return []


def main() -> int:
    problems = check()
    if problems:
        for p in problems:
            print("FAIL", p)
        return 1
    print("OK 文档覆盖全部观察值键：" + str(len(code_keys())) + " 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
