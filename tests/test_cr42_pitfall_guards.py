"""CR-42 踩坑守护（对应 docs/spec/agentlisp_lessons_ledger.md 的判据列）。

每个用例都对应台账里的一条坑。这些断言在坑复发时会立刻变红，
因此「记录」不再是文档纪律，而是可执行判据。
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HAS_RACKET = shutil.which("racket") is not None
FIX = ROOT / "tests" / "patterns" / "fixtures_v2"

pytestmark = pytest.mark.skipif(not HAS_RACKET, reason="racket not on PATH")


def _v2_macros() -> list[str]:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from gen_patterns_v2 import PATTERNS

    return [p["macro"] for p in PATTERNS]


def test_all_v2_macros_are_whitelisted() -> None:
    """坑 #4：宏没登记进 main.rkt 白名单时会静默不展开（产物是原式）。"""
    main = (ROOT / "compiler" / "main.rkt").read_text(encoding="utf-8")
    start = main.index("(define pattern-macro-names")
    seg = main[start : start + 900]
    listed = set(re.findall(r"(def[a-z0-9-]+-agent)", seg))
    missing = sorted(set(_v2_macros()) - listed)
    assert not missing, f"这些宏定义了但没登记白名单，将静默不展开：{missing}"


def test_fixture_agent_name_matches_key_scene() -> None:
    """坑 #5：agent 名必须是 <key>_<scene>，写成文件名就不会命中 HC 分支。"""
    bad = []
    for al in sorted(FIX.glob("*.al")):
        stem = al.stem  # 形如 priority01_hc_HC
        parts = stem.split("_")
        if len(parts) < 3:
            continue
        expected_name = "_".join(parts[:-1])  # priority01_hc
        text = al.read_text(encoding="utf-8")
        m = re.match(r"\s*\(\s*([a-z0-9-]+)\s+([^\s)]+)", text)
        if not m:
            bad.append(f"{al.name}: 无法解析宏调用")
            continue
        if m.group(2) != expected_name:
            bad.append(f"{al.name}: agent 名={m.group(2)}，应为 {expected_name}")
    assert not bad, "夹具 agent 名不规范：\n" + "\n".join(bad)


def test_no_prompt_only_semantics_in_fixtures() -> None:
    """坑 #6：P-4 之后语义标记只能由 (:pattern ...) 承载，不得回到 system-prompt。"""
    offenders = [
        p.name for p in FIX.glob("*.expected.rkt") if "约束：" in p.read_text(encoding="utf-8")
    ]
    assert not offenders, f"这些夹具的提示词里又出现「约束：」语义段：{offenders}"


def test_every_registered_kind_has_a_producer() -> None:
    """坑 #7：注册了 kind 却没人产出 —— 覆盖会静默退化。"""
    expr = (
        '(require (file "' + str(ROOT / "compiler" / "pattern_registry.rkt") + '"))'
        " (for ([k (in-list (pattern-kinds))]) (displayln k))"
    )
    cp = subprocess.run(["racket", "-e", expr], capture_output=True, text=True, timeout=60)
    kinds = {line.strip() for line in cp.stdout.splitlines() if line.strip()}
    produced = set()
    # V1 五宏的产出在 fixtures/（旧目录），V2 十六宏在 fixtures_v2/，两处都要扫
    for exp in list(FIX.glob("*.expected.rkt")) + list(
        (ROOT / "tests" / "patterns" / "fixtures").glob("*.expected.rkt")
    ):
        for m in re.finditer(r":kind\s+([a-z0-9-]+)", exp.read_text(encoding="utf-8")):
            produced.add(m.group(1))
    missing = sorted(kinds - produced)
    assert not missing, f"这些 kind 已注册但没有任何夹具产出：{missing}"


def test_ast_gate_count_matches_fixture_total() -> None:
    """坑 #8：闸门汇总文案的分母必须等于实际夹具数（曾写死 30/30）。"""
    total = len(list(FIX.glob("*.expected.rkt")))
    cp = subprocess.run(
        ["python3", "scripts/check_patterns_v2_ast.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert cp.returncode == 0, cp.stdout[-400:]
    m = re.search(r"AST OK \((\d+)/(\d+)", cp.stdout)
    assert m, f"闸门输出未含计数：{cp.stdout[-200:]}"
    assert int(m.group(1)) == total == int(m.group(2)), (
        f"闸门计数 {m.group(1)}/{m.group(2)} 与实际夹具数 {total} 不一致"
    )
