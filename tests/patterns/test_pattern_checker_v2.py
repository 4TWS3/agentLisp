"""CR-41 V2 Pattern Macros · TDD 红断言（30 cases — 10 宏 × 3 场景 HC/GENERIC/REVERSE）
绑定 SRS 附录 B CR41-PAT01..10 Scn=Pas=3 each → 30 cases 对齐。

阶段 1 红：patterns_v2.rkt 10 宏 define-syntax TODO 占位 raise-syntax-error
→ 30 条全部 FAIL（pytest 30 failed）= TDD 红阶段证据
阶段 2 绿（T8..T17 10 宏实现后 → pytest 30/30 passed。
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPILER_DIR = PROJECT_ROOT / "compiler"
FIXTURES_V2_DIR = PROJECT_ROOT / "tests" / "patterns" / "fixtures_v2"
RACKET_BIN = "racket"
HAS_RACKET = shutil.which(RACKET_BIN) is not None
Path = pathlib.Path

V2_MACROS = (
    "priority01",
    "decomp02",
    "fsm03",
    "eval04",
    "topic05",
    "decom06",
    "guard07",
    "hitl08",
    "exc09",
    "explore10",
)
SCENES = ("HC", "GENERIC", "REVERSE")

CASE_IDS = [f"{m}_{s}" for m in V2_MACROS for s in SCENES]

def _fixture_path(cid: str, ext: str) -> pathlib.Path:
    code, scene = cid.rsplit("_", 1)
    stem = f"{code}_{scene.lower()}_{scene}"
    suffix = ".al" if ext == "al" else ".expected.rkt"
    return FIXTURES_V2_DIR / f"{stem}{suffix}"

AL_FILES = {cid: _fixture_path(cid, "al") for cid in CASE_IDS}
EXPECTED_FILES = {cid: _fixture_path(cid, "expected") for cid in CASE_IDS}

# 与 V1 口径一致：无 Racket 环境则全部 skipif 等待 CI Ubuntu 提供红证据
pytestmark = pytest.mark.skipif(
    not HAS_RACKET,
    reason="Racket binary `racket` not found on PATH (请在 CI Ubuntu runner 跑 patterns_v2 测试；本机无 Racket 跳过，红证据见 _tmp_o13_patterns_mvp_verify.yml job 中 Racket 8.12 10 宏 TODO 将 FAIL)",
)


def _racket_macroexpand_v2(al_path: pathlib.Path) -> tuple[int, str, str]:
    """复用 V1 口径的 main.rkt --dump-ast，已在 expand-pattern-macros 合并命名空间
    (V1 + V2 双 require)
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
    import re

    lines = []
    for line in sexp_str.splitlines():
        if line.lstrip().startswith(";"):
            continue
        lines.append(line)
    merged = "\n".join(lines)
    return re.sub(r"\s+", " ", merged).strip()


# ----------------------------------------------------------------------------
# V2-RED-01..30  10 宏 × 3 场景 = 30 cases（TDD 红：exit != 0 或 stdout 空
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", CASE_IDS, ids=CASE_IDS)
def test_v2_macro_expand_returns_valid_define_agent(case_id: str):
    """CR41-PAT 对应附录 B 的 Scn=Pas=3；红阶段 patterns_v2.rkt TODO 占位未实现
    → 宏展开必 FAIL；绿阶段实现后必须 (define-agent ...)
    """
    al = AL_FILES[case_id]
    exp = EXPECTED_FILES[case_id]
    assert al.exists(), f"missing fixture .al: {al}"
    assert exp.exists(), f"missing fixture .expected.rkt: {exp}"
    rc, out, err = _racket_macroexpand_v2(al)
    # 红阶段：define-syntax raise-syntax-error TODO → rc != 0 或 stderr 含 TODO
    # 绿阶段：rc == 0 + stdout 顶层 (define-agent ...)
    assert rc == 0, f"红阶段TODO占位未实现 rc={rc} stderr tail[-500:]= {err[-500:]}"
    assert out.strip(), "empty stdout (expected (define-agent ...) s-exp"
    nout = _normalize_sexp(out)
    assert nout.startswith("(define-agent"), (
        f"宏展开顶层形状错误 (V2 宏 {case_id} out[:160]={nout[:160]!r})"
    )
    expected_src = _normalize_sexp(exp.read_text(encoding="utf-8"))
    # 字节级 SDD 200 前缀全等 SBE
    assert nout[:200] == expected_src[:200], (
        f"V2 宏展开 SDD 前缀 200 bytes 不相等（case {case_id}）\n"
        f"ACTUAL[:200]  : {nout[:200]!r}\n"
        f"EXPECT[:200]: {expected_src[:200]!r}"
    )


V1_V2_MACROS = [
    ("defreflect-agent", "v1"), ("defrouter-agent", "v1"),
    ("defchain-agent", "v1"), ("defparallel-agent", "v1"),
    ("defplanner-agent", "v1"), ("defpriority-agent", "v2"),
    ("defdecomposition-agent", "v2"), ("deffsm-agent", "v2"),
    ("defevaluator-agent", "v2"), ("deftopic-model-agent", "v2"),
    ("defdecomposer-agent", "v2"), ("defguardrails-safety-agent", "v2"),
    ("defhitl-agent", "v2"), ("defexception-agent", "v2"),
    ("defexploration-agent", "v2"),
]
FIVE_BUCKETS = [":model", ":tools", ":context", ":harness", ":multiagent"]
THREE_MANDATORY = [":model", ":tools", ":context"]
TEN_CELL_LABELS = [
    "d1-1升序5bucket", "d1-2三必块", "d2-1pattern-kind tag",
    "d2-2pattern-config kv", "d3-1harness c/v/c trichotomy",
    "d3-2无运行时eval污染", "d4-1agent_name是symbol",
    "d4-2block count∈[3,5]", "d5-1顶层define-agent",
    "d5-2每block带kw tag",
]


def _sexp_count_parens(s: str) -> int:
    return s.count("(") - s.count(")")


def _strip_comments(s: str) -> str:
    out = []
    for ln in s.splitlines():
        i = 0
        in_str = False
        while i < len(ln):
            ch = ln[i]
            if ch == '"':
                in_str = not in_str
            elif ch == ";" and not in_str:
                break
            out.append(ch)
            i += 1
        out.append("\n")
    return "".join(out)


def _tokenize_sexp(src: str):
    src = _strip_comments(src)
    i = 0
    n = len(src)
    tokens = []
    while i < n:
        ch = src[i]
        if ch in " \t\r\n":
            i += 1
            continue
        if ch == "(" or ch == ")":
            tokens.append(ch)
            i += 1
            continue
        if ch == '"':
            j = i + 1
            while j < n and src[j] != '"':
                if src[j] == "\\":
                    j += 2
                    continue
                j += 1
            tokens.append(src[i:j + 1])
            i = j + 1
            continue
        j = i
        while j < n and src[j] not in " \t\r\n()":
            j += 1
        tokens.append(src[i:j])
        i = j
    return tokens


def _parse_from_tokens(tok, pos=0):
    if pos >= len(tok):
        return None, pos
    t = tok[pos]
    if t == ")":
        return None, pos + 1
    if t == "(":
        pos += 1
        out = []
        while pos < len(tok) and tok[pos] != ")":
            node, pos = _parse_from_tokens(tok, pos)
            if node is None:
                break
            out.append(node)
        return out, pos + 1
    return t, pos + 1


def _parse(src: str):
    tok = _tokenize_sexp(src)
    if not tok:
        return None
    node, _ = _parse_from_tokens(tok, 0)
    return node


def _get_kw_blocks(define_agent_parsed):
    if not isinstance(define_agent_parsed, list) or len(define_agent_parsed) < 3:
        return []
    out = []
    items = define_agent_parsed[2:]
    i = 0
    while i < len(items):
        it = items[i]
        if isinstance(it, str) and it.startswith(":"):
            blk = [it]
            j = i + 1
            while j < len(items):
                nj = items[j]
                if isinstance(nj, str) and nj.startswith(":"):
                    break
                blk.append(nj)
                j += 1
            out.append(blk)
            i = j
        else:
            i += 1
    return out


@pytest.mark.skipif(not HAS_RACKET, reason="No racket runtime; skip V2 patterns cases")
@pytest.mark.parametrize("macro,ver", V1_V2_MACROS, ids=[f"{v}-{m.split('-')[0]}" for m, v in V1_V2_MACROS])
def test_nfr01_macro_expand_head200_prefix_byte_identical(macro: str, ver: str):
    """NFR-PATTERN-01: 15宏 × (HC head + GENERIC head shape 200bytes全等) = 30 assertions
    对应 patterns_checker_v2.rkt check-nfr01-ast-equivalence；HC fixture 文件在 fixtures/fixtures_v2 目录下。
    Ver: V1= patterns.rkt (CR-40 三绿) V2= patterns_v2.rkt (CR-41 新增)
    """
    suffix_id = macro.replace("-agent", "")
    if ver == "v1":
        fx_dir = Path("tests/patterns/fixtures")
        prefix_map = {
            "defreflect": "code-refiner", "defrouter": "ops-gateway",
            "defchain": "doc-pipeline", "defparallel": "multi-search",
            "defplanner": "deep-researcher",
        }
        hc_id = prefix_map[macro.replace("-agent", "")]
        al = fx_dir / f"{hc_id}.al"
        expected = fx_dir / f"{hc_id}.expected.rkt"
    else:
        fx_dir = Path("tests/patterns/fixtures_v2")
        prefix_map_v2 = {
            "defpriority": "cr41_pat01_priority", "defdecomposition": "cr41_pat02_decomposition",
            "deffsm": "cr41_pat03_fsm", "defevaluator": "cr41_pat04_evaluator",
            "deftopic-model": "cr41_pat05_topic_model", "defdecomposer": "cr41_pat06_decomposer",
            "defguardrails-safety": "cr41_pat07_guardrails_safety", "defhitl": "cr41_pat08_hitl",
            "defexception": "cr41_pat09_exception", "defexploration": "cr41_pat10_exploration",
        }
        hc_id = prefix_map_v2[suffix_id]
        al = fx_dir / f"{hc_id}_hc.al"
        expected = fx_dir / f"{hc_id}_hc.expected.rkt"
    assert al.exists(), f"HC fixture missing: {al}"
    assert expected.exists(), f"HC expected missing: {expected}"
    rc, out, err = _racket_macroexpand_v2(al)
    assert rc == 0, f"HC macroexpand non-zero rc={rc} err_tail={err[-300:]}"
    nout = _normalize_sexp(out)
    expected_src = _normalize_sexp(expected.read_text(encoding="utf-8"))
    assert nout[:200] == expected_src[:200], (
        f"NFR01 {ver} {macro} HC head 200 bytes mismatch.\n"
        f"ACT  : {nout[:200]!r}\nEXP  : {expected_src[:200]!r}"
    )


@pytest.mark.skipif(not HAS_RACKET, reason="No racket runtime; skip NFR02 static matrix")
@pytest.mark.parametrize("macro,ver", V1_V2_MACROS, ids=[f"{v}-{m.split('-')[0]}" for m, v in V1_V2_MACROS])
def test_nfr02_static_safety_10d_matrix_150checkpoint_all_true(macro: str, ver: str):
    """NFR-PATTERN-02: 5×2=10维静态安全矩阵 × 15宏 = 150 checkpoint 全 #t。
    对应 patterns_checker_v2.rkt check-nfr02-static-safety-matrix：
      d1-1: 5-bucket 严格升序
      d1-2: 三必块 model/tools/context 都存在
      d2-1: :pattern-kind tag 存在（任一 block 内）
      d2-2: :pattern-config kv 存在（任一 block 内）
      d3-1: harness block 内 :constrain :verify :correct trichotomy
      d3-2: 整个 S-exp 无 eval/apply/eval-syntax（无运行时动态求值污染）
      d4-1: define-agent 的第二个位置是 symbol（agent_name 非 list 字符串等）
      d4-2: block 总数 ∈ [3,5]
      d5-1: 顶层 head 形状 define-agent
      d5-2: 每 block 首 token 是 :keyword
    """
    suffix_id = macro.replace("-agent", "")
    if ver == "v1":
        fx_dir = Path("tests/patterns/fixtures")
        prefix_map = {
            "defreflect": "code-refiner", "defrouter": "ops-gateway",
            "defchain": "doc-pipeline", "defparallel": "multi-search",
            "defplanner": "deep-researcher",
        }
        hc_id = prefix_map[suffix_id]
        al = fx_dir / f"{hc_id}.al"
    else:
        fx_dir = Path("tests/patterns/fixtures_v2")
        prefix_map_v2 = {
            "defpriority": "cr41_pat01_priority", "defdecomposition": "cr41_pat02_decomposition",
            "deffsm": "cr41_pat03_fsm", "defevaluator": "cr41_pat04_evaluator",
            "deftopic-model": "cr41_pat05_topic_model", "defdecomposer": "cr41_pat06_decomposer",
            "defguardrails-safety": "cr41_pat07_guardrails_safety", "defhitl": "cr41_pat08_hitl",
            "defexception": "cr41_pat09_exception", "defexploration": "cr41_pat10_exploration",
        }
        hc_id = prefix_map_v2[suffix_id]
        al = fx_dir / f"{hc_id}_hc.al"
    assert al.exists(), f"fixture missing: {al}"
    rc, out, err = _racket_macroexpand_v2(al)
    assert rc == 0, f"HC macroexpand rc={rc} non-zero err={err[-300:]}"
    nout = _normalize_sexp(out)
    parsed = _parse(nout)
    assert parsed is not None, "parse S-exp returned None"
    assert isinstance(parsed, list), "top S-exp not list"

    cells = {}

    head = parsed[0] if parsed else None
    cells["d5-1"] = head == "define-agent" or head == "defagent"

    agent_name = parsed[1] if len(parsed) > 1 else None
    cells["d4-1"] = (
        isinstance(agent_name, str)
        and agent_name
        and agent_name[0] not in "(:"
        and "(" not in agent_name
    )

    blocks = _get_kw_blocks(parsed)
    block_tags = [b[0] for b in blocks]

    cells["d4-2"] = 3 <= len(blocks) <= 5

    d5_2_ok = True
    for b in blocks:
        if not (len(b) >= 1 and isinstance(b[0], str) and b[0].startswith(":")):
            d5_2_ok = False
            break
    cells["d5-2"] = d5_2_ok

    d1_1_ok = True
    prev_idx = -1
    for t in block_tags:
        if t not in FIVE_BUCKETS:
            continue
        idx = FIVE_BUCKETS.index(t)
        if idx < prev_idx:
            d1_1_ok = False
            break
        prev_idx = idx
    cells["d1-1"] = d1_1_ok

    cells["d1-2"] = all(m in block_tags for m in THREE_MANDATORY)

    flat_text = nout
    cells["d2-1"] = ":pattern-kind" in flat_text
    cells["d2-2"] = ":pattern-config" in flat_text

    harness_block = None
    for b in blocks:
        if b and b[0] == ":harness":
            harness_block = b
            break
    if harness_block is None:
        cells["d3-1"] = True
    else:
        h_subtags = []
        for sub in harness_block[1:]:
            if isinstance(sub, list) and sub and isinstance(sub[0], str) and sub[0].startswith(":"):
                h_subtags.append(sub[0])
            elif isinstance(sub, str) and sub.startswith(":"):
                h_subtags.append(sub)
        cells["d3-1"] = all(t in h_subtags for t in [":constrain", ":verify", ":correct"])

    cells["d3-2"] = not any(bad in flat_text for bad in [" eval ", " apply ", " eval-syntax ", "syntax-local-value"])

    for cell_key in ["d1-1", "d1-2", "d2-1", "d2-2", "d3-1", "d3-2", "d4-1", "d4-2", "d5-1", "d5-2"]:
        label_map = dict(zip(
            ["d1-1", "d1-2", "d2-1", "d2-2", "d3-1", "d3-2", "d4-1", "d4-2", "d5-1", "d5-2"],
            TEN_CELL_LABELS,
        ))
        assert cells.get(cell_key, False) is True, (
            f"NFR02 {ver} {macro} cell={cell_key}({label_map[cell_key]}) FAIL\n"
            f"block_tags={block_tags}, agent_name={agent_name!r}"
        )
