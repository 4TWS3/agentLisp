"""CR-42 F4：语义标记独立断言（SRS 声明 ↔ patterns_v2.rkt 实际展开产物，双向）。

背景（CR-41 独立审计 finding 4）：仓库里唯一的 markers 检查在
scripts/check_patterns_v2_ast.py L281-283，其 oracle 是生成器自己的
gen_patterns_v2.PATTERNS[*]["markers"] —— 生成器自己验自己（自证），
SRS 文本与产物之间没有任何机器校验。

本测试把两侧换成互相独立的事实源：
  A 侧（声明）：docs/spec/agentlisp_srs.md §3 CR41-PAT01..10 行（审计判据 L104-113）。
  B 侧（产物）：racket compiler/main.rkt --dump-ast <fixture> 的 stdout，
               即 compiler/patterns_v2.rkt 宏的真实展开结果（含 system-prompt 文本）。

双向断言：
  D1（SRS → 产物）：SRS 声明的每个语义标记必须出现在该宏展开产物的全文里。
  D2（产物 → SRS）：产物 system-prompt「约束：」段里出现的每个语义标记，
                    必须能在 SRS 的 CR41-PAT 行里找到声明（§3 主行 ∪ 附录 B 行）。
                    用户参数回显（fixture plist 注进「模式参数：」段的 token）不计入标记。

本模块不 import scripts.gen_patterns_v2，也不 import scripts.check_patterns_v2_ast：
SRS 行与 racket 产物是仅有的两个输入。
"""

from __future__ import annotations

import functools
import pathlib
import re
import shutil
import subprocess

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SRS_PATH = PROJECT_ROOT / "docs" / "spec" / "agentlisp_srs.md"
FIXTURES_V2_DIR = PROJECT_ROOT / "tests" / "patterns" / "fixtures_v2"

# 审计判据：SRS §3 CR41-PAT01..10 锚点行位于 L104-L113 附近。
SRS_ANCHOR_WINDOW = (95, 130)

# macro → (CR41-PAT id, fixture stem)
V2_MACRO_PATTERNS = (
    ("defpriority-agent", "CR41-PAT01", "priority01"),
    ("defdecomposition-agent", "CR41-PAT02", "decomp02"),
    ("deffsm-agent", "CR41-PAT03", "fsm03"),
    ("defevaluator-agent", "CR41-PAT04", "eval04"),
    ("deftopic-model-agent", "CR41-PAT05", "topic05"),
    ("defdecomposer-agent", "CR41-PAT06", "decom06"),
    ("defguardrails-safety-agent", "CR41-PAT07", "guard07"),
    ("defhitl-agent", "CR41-PAT08", "hitl08"),
    ("defexception-agent", "CR41-PAT09", "exc09"),
    ("defexploration-agent", "CR41-PAT10", "explore10"),
)
SCENES = ("HC", "GENERIC")

# 语义标记文法：小写 kebab-case 标识符（≥2 段）。大写开头（NFR-SEC / IF-TEMPORAL-1）
# 与 :keyword（:model）不会命中；纯单词（budget / convergence）不算标记。
MARKER_RE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)+")

# 展开机制词汇：这些 token 描述宏的展开入口/展开语义，按定义不会出现在展开产物里，
# 因此不能作为「SRS → 产物」的判据。宏入口名（def*-agent）由 _is_entry_name 识别。
EXPANSION_MECHANISM_TOKENS = frozenset({"syntax-case", "first-match"})

PROMPT_PARAMS_ANCHOR = "模式参数："
PROMPT_CONSTRAINT_ANCHOR = "约束："

# 「模式参数：…。」段是 fixture plist 的回显（用户输入），不是宏模板声明的语义标记。
# 当前 10 个 HC fixture 中，只有 priority01 的参数名 priority-level 同时出现在约束句里。
EXPECTED_PARAM_ECHO_MARKERS = frozenset({"priority-level"})

HAS_RACKET = shutil.which("racket") is not None


def _is_entry_name(tok: str) -> bool:
    return bool(re.fullmatch(r"def[a-z0-9-]*-agent", tok))


def _row_id(line: str) -> str | None:
    m = re.match(r"^\| \*\*(CR41-PAT\d\d)\*\* \|", line)
    return m.group(1) if m else None


def _load_srs_rows() -> tuple[list[tuple[int, str, str]], list[tuple[int, str, str]]]:
    """返回 (primary_rows, appendix_rows)，元素 = (行号, 行文本, PAT id)。

    primary = 文件中按行序首次出现的 10 个 CR41-PAT 行（§3 声明锚点）；
    appendix = 其余 CR41-PAT 行（附录 B 计分行），用于 D2 的声明集合。
    """
    rows = []
    for no, line in enumerate(SRS_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        pat = _row_id(line)
        if pat:
            rows.append((no, line, pat))
    primary, appendix, seen = [], [], set()
    for row in rows:
        if row[2] not in seen:
            seen.add(row[2])
            primary.append(row)
        else:
            appendix.append(row)
    return primary, appendix


def _marker_tokens(text: str) -> set[str]:
    return set(MARKER_RE.findall(text))


def _declared_by_pattern(rows) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for _no, line, pat in rows:
        out.setdefault(pat, set()).update(_marker_tokens(line))
    return out


def _strip_mechanism(tokens: set[str]) -> set[str]:
    return {t for t in tokens if not _is_entry_name(t) and t not in EXPANSION_MECHANISM_TOKENS}


@functools.cache
def _expand_fixture(al_path: pathlib.Path) -> str:
    """运行真实展开通路，返回归一化后的产物全文（stdout）。

    lru_cache：同一 fixture 在一个 pytest 进程内只 spawn 一次 racket
    （D1 覆盖 HC/GENERIC，D2 复用 HC）。
    """
    proc = subprocess.run(
        ["racket", "compiler/main.rkt", "--dump-ast", str(al_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"racket 展开失败 rc={proc.returncode} fixture={al_path.name}\n"
        f"stderr tail: {proc.stderr[-400:]}"
    )
    return " ".join(proc.stdout.split())


def _extract_system_prompt(product_text: str) -> str:
    """从展开产物里取出 :system-prompt 的字符串值（不依赖正则转义层）。"""
    key = ':system-prompt "'
    start = product_text.find(key)
    if start < 0:
        return ""
    i = start + len(key)
    buf: list[str] = []
    while i < len(product_text):
        ch = product_text[i]
        if ch == "\\":
            buf.append(product_text[i : i + 2])
            i += 2
            continue
        if ch == '"':
            break
        buf.append(ch)
        i += 1
    return "".join(buf)


def _split_prompt_segments(prompt: str) -> tuple[str, str]:
    """切出 (参数回显段, 约束段)。"""
    if PROMPT_CONSTRAINT_ANCHOR not in prompt:
        return prompt, ""
    params_part = prompt.split(PROMPT_PARAMS_ANCHOR, 1)[-1]
    params_seg, cons_seg = params_part.split(PROMPT_CONSTRAINT_ANCHOR, 1)
    return params_seg, cons_seg


def check_markers(
    declared_primary: set[str],
    declared_all: set[str],
    product_text: str,
    prompt: str,
) -> list[str]:
    """纯函数：双向标记比对，返回违规列表（空 = 通过）。

    D1：declared_primary 的每个标记必须出现在 product_text。
    D2：约束段里的标记（去掉参数回显）必须在 declared_all 里有声明。
    """
    violations: list[str] = []
    product_tokens = _marker_tokens(product_text)
    for tok in sorted(declared_primary):
        if tok not in product_tokens:
            violations.append(f"D1 SRS 声明标记未出现在展开产物: {tok!r}")
    params_seg, cons_seg = _split_prompt_segments(prompt)
    param_echo = _marker_tokens(params_seg)
    for tok in sorted(_marker_tokens(cons_seg) - param_echo):
        if tok not in declared_all:
            violations.append(f"D2 产物出现 SRS 未声明标记: {tok!r}")
    return violations


# ---------------------------------------------------------------- 锚点与文法自检


def test_srs_anchor_rows_located_at_declared_lines():
    """§3 的 10 个 CR41-PAT 声明行必须仍在 SRS 的 L104-L113 附近。"""
    primary, appendix = _load_srs_rows()
    assert len(primary) == 10, f"CR41-PAT 主声明行数 = {len(primary)}，期望 10"
    assert len(appendix) >= 10, "附录 B CR41-PAT 计分行缺失"
    lines = [no for no, _l, _p in primary]
    lo, hi = SRS_ANCHOR_WINDOW
    assert all(lo <= no <= hi for no in lines), (
        f"CR41-PAT 声明行已漂移出审计判据窗口 L{lo}-L{hi}: {lines}"
    )
    # 10 个声明行必须覆盖 CR41-PAT01..10 全集
    assert {p for _n, _l, p in primary} == {p for _m, p, _s in V2_MACRO_PATTERNS}


def test_marker_checker_is_falsifiable_in_both_directions():
    """反例自检：D1 缺标记、D2 造未声明标记都必须被判红。

    这是本测试「能红」的常驻证据（不依赖临时改源码）：
    """
    declared_primary = {"decomp-level-1", "scoped-worker"}
    declared_all = {"decomp-level-1", "scoped-worker", "on-violation"}
    good_product = (
        '(define-agent x (:model :system-prompt "约束：decomp-level-1；scoped-worker。"))'
    )
    good_prompt = "约束：decomp-level-1；scoped-worker。"
    assert check_markers(declared_primary, declared_all, good_product, good_prompt) == []

    # D1 反例：删掉 scoped-worker
    bad_product = '(define-agent x (:model :system-prompt "约束：decomp-level-1。"))'
    v1 = check_markers(declared_primary, declared_all, bad_product, "约束：decomp-level-1。")
    assert any(v.startswith("D1") and "scoped-worker" in v for v in v1), v1

    # D2 反例：产物凭空多出 SRS 未声明的 super-secret-mode
    bad_product2 = '(define-agent x (:model :system-prompt "约束：decomp-level-1；scoped-worker；super-secret-mode。"))'
    v2 = check_markers(
        declared_primary,
        declared_all,
        bad_product2,
        "约束：decomp-level-1；scoped-worker；super-secret-mode。",
    )
    assert any(v.startswith("D2") and "super-secret-mode" in v for v in v2), v2


# ------------------------------------------------------------------ 双向主断言


@pytest.mark.skipif(
    not HAS_RACKET, reason="需要 racket 才能取 compiler/patterns_v2.rkt 的真实展开产物"
)
@pytest.mark.parametrize(
    "macro,pat,stem", V2_MACRO_PATTERNS, ids=[f"{p}-{s}" for _m, p, s in V2_MACRO_PATTERNS]
)
def test_srs_declared_markers_all_present_in_product(macro, pat, stem):
    """D1：SRS §3 声明的语义标记必须出现在该宏的展开产物中。"""
    primary, appendix = _load_srs_rows()
    declared_primary = _strip_mechanism(_declared_by_pattern(primary)[pat])
    declared_all = _strip_mechanism(_declared_by_pattern(primary + appendix)[pat])
    for scene in SCENES:
        al = FIXTURES_V2_DIR / f"{stem}_{scene.lower()}_{scene}.al"
        assert al.exists(), f"fixture missing: {al}"
        product = _expand_fixture(al)
        prompt = _extract_system_prompt(product)
        violations = check_markers(declared_primary, declared_all, product, prompt)
        assert not [v for v in violations if v.startswith("D1")], (
            f"{pat} {macro} {scene}: {violations}"
        )


@pytest.mark.skipif(
    not HAS_RACKET, reason="需要 racket 才能取 compiler/patterns_v2.rkt 的真实展开产物"
)
@pytest.mark.parametrize(
    "macro,pat,stem", V2_MACRO_PATTERNS, ids=[f"{p}-{s}" for _m, p, s in V2_MACRO_PATTERNS]
)
def test_no_undeclared_markers_in_product_prompt(macro, pat, stem):
    """D2：产物「约束：」段不得出现 SRS 未声明的语义标记（参数回显除外）。"""
    primary, appendix = _load_srs_rows()
    declared_primary = _strip_mechanism(_declared_by_pattern(primary)[pat])
    declared_all = _strip_mechanism(_declared_by_pattern(primary + appendix)[pat])
    al = FIXTURES_V2_DIR / f"{stem}_hc_HC.al"
    assert al.exists(), f"fixture missing: {al}"
    product = _expand_fixture(al)
    prompt = _extract_system_prompt(product)
    violations = check_markers(declared_primary, declared_all, product, prompt)
    assert not [v for v in violations if v.startswith("D2")], f"{pat} {macro}: {violations}"
    # 护栏：参数回显排除规则当前只允许屏蔽 priority01 的 priority-level。
    # 若未来该规则开始吞掉真实标记，这行断言会先红。
    params_seg, cons_seg = _split_prompt_segments(prompt)
    echo = _marker_tokens(params_seg) & _marker_tokens(cons_seg)
    assert echo <= EXPECTED_PARAM_ECHO_MARKERS, (
        f"参数回显排除集合扩大到 {sorted(echo)}，可能掩盖真实标记缺失"
    )
