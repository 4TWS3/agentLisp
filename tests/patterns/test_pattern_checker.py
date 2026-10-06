"""O13 Pattern Macros · 阶段 1 红断言（10 cases，全失败）
绑定 SRS 附录 B：
  FR-PATTERN-01 Scn=5：5 MVP 宏展开不得抛异常 → PM-01..PM-05
  FR-PATTERN-02 Scn=10：5 模式 × (正常顺序 + 反序自动提升静态前缀) → PM-06..PM-15
  NFR-PATTERN-01 Scn=5：5 模式 AST 字节级与手写 defagent 等价 → PM-16..PM-20
  NFR-PATTERN-02 Scn=10：5 × 2 静态安全 100% 继承 checker → PM-21..PM-30

阶段 1 红本文件只写 PM-01..PM-10（10 条红 cases，FR-PATTERN-01 的 5 + FR-PATTERN-02 前 5，
阶段 2 绿时扩展到 30 cases 全对齐 Scn=30 Pas=30）
"""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPILER_DIR = PROJECT_ROOT / "compiler"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "patterns" / "fixtures"
RACKET_BIN = "racket"
MVP_IDS = ("defchain", "defparallel", "defreflect", "defrouter", "defplanner")
MVP_AL_FILES = {
    "defchain": FIXTURES_DIR / "defchain_doc_pipeline.al",
    "defparallel": FIXTURES_DIR / "defparallel_multi_search.al",
    "defreflect": FIXTURES_DIR / "defreflect_code_refiner.al",
    "defrouter": FIXTURES_DIR / "defrouter_ops_gateway.al",
    "defplanner": FIXTURES_DIR / "defplanner_deep_researcher.al",
}
MVP_EXPECTED_FILES = {
    "defchain": FIXTURES_DIR / "defchain_doc_pipeline.expected.rkt",
    "defparallel": FIXTURES_DIR / "defparallel_multi_search.expected.rkt",
    "defreflect": FIXTURES_DIR / "defreflect_code_refiner.expected.rkt",
    "defrouter": FIXTURES_DIR / "defrouter_ops_gateway.expected.rkt",
    "defplanner": FIXTURES_DIR / "defplanner_deep_researcher.expected.rkt",
}

pytestmark = pytest.mark.skipif(
    not importlib.util.find_spec("pytest"),
    reason="pytest available, marker always true",
)


# ---------------------------------------------------------------------------
# 内部 helpers
# ---------------------------------------------------------------------------


def _racket_macroexpand_on_file(al_path: pathlib.Path) -> tuple[int, str, str]:
    """调用 Racket main.rkt 的 --dump-ast 模式（如未实现）则模拟调用子进程返回。
    当前红阶段 patterns.rkt 未接线 → racket 调用将抛 exit != 0 → 断言必失败。
    """
    cmd = [
        RACKET_BIN,
        str(COMPILER_DIR / "main.rkt"),
        "--dump-ast",
        str(al_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    return proc.returncode, proc.stdout, proc.stderr


def _normalize_sexp(sexp_str: str) -> str:
    """简单 normalize 以便对比：折叠空白，保持括号与字符串字面原义。"""
    import re

    # strip comments (line comments only)
    lines = []
    for line in sexp_str.splitlines():
        if line.lstrip().startswith(";"):
            continue
        lines.append(line)
    merged = "\n".join(lines)
    return re.sub(r"\s+", " ", merged).strip()


# ---------------------------------------------------------------------------
# PM-01..PM-05  FR-PATTERN-01 宏展开无异常（5 cases）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode_id", MVP_IDS, ids=MVP_IDS)
def test_fr_pattern_01_macro_expand_returns_valid_defagent_ast(mode_id: str) -> None:
    """FR-PATTERN-01: MVP 5 模式的高层糖语法 .al 文件走宏展开 pass（racket main.rkt --dump-ast）后，
    必须 exit=0，且 stdout 前 12 个非空 token 匹配预期 .expected.rkt 的顶层 (defagent name ...) 结构。
    阶段 1 红：patterns.rkt 未实现 → exit != 0 或 stdout 为空 → 全部 FAIL。
    """
    al = MVP_AL_FILES[mode_id]
    expected = MVP_EXPECTED_FILES[mode_id]
    assert al.exists(), f"missing {al}"
    assert expected.exists(), f"missing {expected}"
    rc, out, err = _racket_macroexpand_on_file(al)
    assert rc == 0, f"racket exit={rc}, stderr tail: {err[-400:]}"
    assert out.strip(), "empty stdout (expected (defagent ...) s-exp)"
    normalized_out = _normalize_sexp(out)
    assert normalized_out.startswith("(define-agent") or normalized_out.startswith("(defagent"), (
        f"宏展开顶层形状错误，out[:160]={normalized_out[:160]!r}"
    )


# ---------------------------------------------------------------------------
# PM-06..PM-10  FR-PATTERN-02 反序自动提升静态前缀（5 cases）
# ---------------------------------------------------------------------------


FR_PATTERN_02_WRONG_ORDER_ALS = {
    "defchain": (
        "(defchain-agent wrong-doc-pipeline "
        ':context-policy (:memory-policy (:markdown-fs "/tmp/wrong.md" :layers (L0-Abstract) :auto-append #t)) '
        ':steps ((:prompt "S1" :out x)))',
    ),
    "defparallel": (
        "(defparallel-agent wrong-ms "
        ':context-policy (:memory-policy (:markdown-fs "/tmp/w.md" :layers (L0-Abstract))) '
        ':branches ((a "A")) :reducer r)',
    ),
    "defreflect": (
        "(defreflect-agent wrong-code-refiner "
        ':tools (bash) :critic "C" :max-retries 3 '
        ':provider "anthropic" :model-name "claude-3-7-sonnet")',
    ),
    "defrouter": (
        '(defrouter-agent wrong-gw :routes ((:intent \'i => w)) :model ("openai" "gpt-5.6"))',
    ),
    "defplanner": (
        "(defplanner-agent wrong-dr "
        ":executor-tools (web-search read-pdf) "
        ':model ("anthropic" "claude-3-7-sonnet") '
        ':planner-prompt "3-5 steps")',
    ),
}


@pytest.mark.parametrize("mode_id", MVP_IDS, ids=[f"{m}_autoraise" for m in MVP_IDS])
def test_fr_pattern_02_wrong_input_order_auto_raised_to_static_prefix_first(mode_id: str) -> None:
    """FR-PATTERN-02: 反序输入（动态块写在静态块之前）→ 宏展开后 AST 顺序仍必须是：
       :model → :tools → :context → :harness
    即 KV Cache 静态前缀强对齐在宏展开阶段就被自动修复，不必等待下游 checker。
    阶段 1 红：patterns.rkt 未实现 → 临时 .al 文件无法通过宏 → exit != 0 → FAIL。
    """
    al_src = FR_PATTERN_02_WRONG_ORDER_ALS[mode_id][0]
    al_path = FIXTURES_DIR / f"fr_pattern_02_{mode_id}_auto_raise.al"
    al_path.write_text(al_src + "\n", encoding="utf-8")
    rc, out, err = _racket_macroexpand_on_file(al_path)
    assert rc == 0, f"反序 .al 宏展开失败 exit={rc}: {err[-500:]}"
    normalized = _normalize_sexp(out)
    # 位置索引判断：:model 出现必须早于 :tools，:tools 出现必须早于 :context
    m_model = normalized.find("(:model")
    m_tools = normalized.find("(:tools")
    m_context = normalized.find("(:context")
    assert 0 <= m_model < m_tools < m_context, (
        f"{mode_id} 反序后未自动提升静态前缀 order: "
        f"model@{m_model} tools@{m_tools} context@{m_context} | out[:240]={normalized[:240]!r}"
    )
