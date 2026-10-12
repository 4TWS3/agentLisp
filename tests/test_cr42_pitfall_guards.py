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
    # 用 importlib 按路径加载，避免改动全局 sys.path
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gen_patterns_v2_mod", ROOT / "scripts" / "gen_patterns_v2.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [p["macro"] for p in mod.PATTERNS]


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
    cp = subprocess.run(
        ["racket", "-e", expr],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
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


def test_no_global_sys_path_mutation_in_tests() -> None:
    """坑 #15：测试里往 sys.path 插 scripts/ 会遮蔽仓库 tests 包。

    scripts/tests/ 存在，一旦 scripts/ 进入 sys.path，import tests 就解析到
    scripts/tests/__init__.py，BDD 动态生成测试随即随机失败（实测 2 红）。
    正解：用 importlib.util.spec_from_file_location 按路径加载。
    """
    offenders = []
    needle_a, needle_b = "sys.path." + "insert", "sys.path." + "append"  # 拆开写，避免匹配到本文件
    for py in (ROOT / "tests").rglob("*.py"):
        if py.resolve() == Path(__file__).resolve():
            continue  # 跳过本守护自身
        text = py.read_text(encoding="utf-8")
        if needle_a in text or needle_b in text:
            offenders.append(str(py.relative_to(ROOT)))
    assert not offenders, f"这些测试文件改了全局 sys.path：{offenders}"


def test_all_expected_fixtures_read_to_eof() -> None:
    """坑 #18：夹具必须能读到 EOF。

    早先我只用 (read) 读一个 datum 就判「READ-OK」，漏掉了文件末尾多余的闭括号，
    结果 CI 的独立校验 5/5 全红。这里读**全部** token，直到 EOF。
    """
    files = sorted((ROOT / "tests" / "patterns" / "fixtures").glob("*.expected.rkt")) + sorted(
        (ROOT / "tests" / "patterns" / "fixtures_v2").glob("*.expected.rkt")
    )
    assert files, "未找到任何 .expected.rkt 夹具"
    bad = []
    for p in files:
        expr = (
            # as_posix()：Windows 路径嵌进 Racket 字符串会被当转义序列（CI 实测）
            '(with-input-from-file "' + p.as_posix() + '" (lambda () (let loop ([n 0]) '
            "(define t (read)) (if (eof-object? t) (void) (loop (add1 n))))))"
        )
        cp = subprocess.run(
            ["racket", "-e", expr],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if cp.returncode != 0:
            bad.append(
                f"{p.name}: {cp.stderr.strip().splitlines()[-1][:90] if cp.stderr.strip() else 'rc!=0'}"
            )
    assert not bad, "这些夹具无法完整读取（读到 EOF）：\n" + "\n".join(bad)


def test_no_scratch_files_are_tracked() -> None:
    """坑 #12 的配套：payload 一律写到 .tmp_* 再执行，但临时文件不得进版本库。"""
    cp = subprocess.run(
        ["git", "ls-files", ".tmp_*"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    tracked = [line for line in cp.stdout.splitlines() if line.strip()]
    assert not tracked, f"这些临时 payload 被提交了：{tracked}"


def test_ast_gate_count_matches_fixture_total() -> None:
    """坑 #8：闸门汇总文案的分母必须等于实际夹具数（曾写死 30/30）。"""
    total = len(list(FIX.glob("*.expected.rkt")))
    cp = subprocess.run(
        ["python3", "scripts/check_patterns_v2_ast.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    assert cp.returncode == 0, cp.stdout[-400:]
    m = re.search(r"AST OK \((\d+)/(\d+)", cp.stdout)
    assert m, f"闸门输出未含计数：{cp.stdout[-200:]}"
    assert int(m.group(1)) == total == int(m.group(2)), (
        f"闸门计数 {m.group(1)}/{m.group(2)} 与实际夹具数 {total} 不一致"
    )
