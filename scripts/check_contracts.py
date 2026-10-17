#!/usr/bin/env python3
"""US-12：21 份契约的机器校验结果（一键报告）。

复用判断，不复制：
  栏位齐备   -> tools/standards_check.py 的 _contract_columns_problems（A12）
  被测试引用 -> 扫 tests/ 是否引用 CT-<KIND>-01（A11 同一判据）
  引擎消费   -> runtime.patterns.KIND_SLOTS

退出码：0 = 21/21 三项全过；1 = 有缺口。
"""

from __future__ import annotations

import importlib.util
import sys

if hasattr(sys.stdout, "reconfigure"):
    # Windows 默认 cp1252：脚本里有中文，不重设会 UnicodeEncodeError（CI 实测）
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "docs" / "spec" / "pattern_runtime_contracts"
TESTS = ROOT / "tests"


def _standards():
    spec = importlib.util.spec_from_file_location(
        "standards_check_mod", ROOT / "tools" / "standards_check.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cid(kind: str) -> str:
    return "CT-" + kind.upper().replace("-", "_") + "-01"


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from runtime.patterns import CONTRACTED, KIND_SLOTS

    sc = _standards()
    problems: list[str] = []
    rows: list[str] = []
    test_texts = [(p, p.read_text(encoding="utf-8")) for p in TESTS.rglob("*.py")]
    for kind in sorted(CONTRACTED):
        path = CONTRACTS / (kind + ".md")
        if not path.is_file():
            problems.append("缺契约 " + kind)
            continue
        cols = sc._contract_columns_problems(path.read_text(encoding="utf-8"))
        cid = _cid(kind)
        ref = any(cid in text for _, text in test_texts)
        slots = KIND_SLOTS[kind]
        ok = not cols and ref
        if cols:
            problems.append(kind + ": " + "；".join(cols))
        if not ref:
            problems.append(kind + ": 无测试引用 " + cid)
        rows.append(
            "  "
            + ("OK " if ok else "BAD")
            + " "
            + kind.ljust(18)
            + " slots="
            + (",".join(slots) if slots else "-")
            + " ref="
            + ("yes" if ref else "no")
        )
    total = len(CONTRACTED)
    print("契约机器校验（" + str(total) + " 份）")
    print(chr(10).join(rows))
    if problems:
        for p in problems:
            print("FAIL", p)
        return 1
    print("OK " + str(total) + "/" + str(total) + " 栏位齐备 + 被测试引用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
