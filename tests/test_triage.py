"""scripts/triage.py 的解析与聚合单测（纯函数，无子进程）。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 用 importlib 按路径加载，避免改动全局 sys.path（会影响同一次 pytest 会话里的其他测试）
_spec = importlib.util.spec_from_file_location("triage_mod", ROOT / "scripts" / "triage.py")
triage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(triage)

SAMPLE = """
=================================== FAILURES ===================================
________ test_nfr02_static_safety_8d_matrix_120checkpoint_all_true[v2-defgoal] ________

    def check():
>       assert cells.get(cell_key, False) is True, (
            f"NFR02 {ver} {macro} cell={cell_key}({label_map[cell_key]}) FAIL\n"
E           AssertionError: NFR02 v2 defgoal-agent cell=d1-2(d1-2三必块) FAIL
E             block_tags=[], agent_name='goal20_hc'
E           assert False is True

________ test_nfr02_static_safety_8d_matrix_120checkpoint_all_true[v2-defrag] ________

    def check():
>       assert cells.get(cell_key, False) is True, (
E           AssertionError: NFR02 v2 defrag-agent cell=d1-2(d1-2三必块) FAIL
E             block_tags=[], agent_name='rag15_hc'
E           assert False is True

________ test_v1_guard ________

E           KeyError: 'defgoal'

=========================== short test summary info ============================
FAILED tests/patterns/test_pattern_checker_v2.py::test_nfr02[v2-defgoal] - AssertionError: NFR02 v2 defgoal-agent cell=d1-2(d1-2三必块) FAIL
FAILED tests/patterns/test_pattern_checker_v2.py::test_nfr02[v2-defrag] - AssertionError: NFR02 v2 defrag-agent cell=d1-2(d1-2三必块) FAIL
FAILED tests/test_cr42_pitfall_guards.py::test_v1_guard - KeyError: 'defgoal'
========================= 2 failed, 1 passed in 1.0s ==========================
"""


def test_normalize_strips_numbers_and_strings() -> None:
    a = triage.normalize("AssertionError: NFR02 v2 defgoal-agent cell=d1-2 FAIL")
    b = triage.normalize("AssertionError: NFR02 v9 defgoal-agent cell=d1-2 FAIL")
    assert a == b, "归一化后同一类报错必须得到同一签名"
    assert "HEXADDR" in triage.normalize("object at 0x106facf00")


def test_parse_aggregates_same_root_cause() -> None:
    rep = triage.parse_pytest_output(SAMPLE)
    assert rep["counts"] == {"passed": 1, "failed": 2, "skipped": 0}
    assert len(rep["failed"]) == 3
    top_sig, top_n = rep["signatures"].most_common(1)[0]
    assert top_n == 2, f"同一根因应聚合 2 次，实际 {top_n}：{top_sig}"
    assert "cell=d" in top_sig, f"签名应保留 cell 形状：{top_sig}"


def test_parse_extracts_cells_and_checker_reasons() -> None:
    rep = triage.parse_pytest_output(SAMPLE)
    assert rep["cells"]["d1-2"] == 2
    assert rep["cell_labels"]["d1-2"] == "d1-2三必块"

    with_checker = "; patterns_checker_v2 FAILED cells: defgoal-agent [5-bucket升序], defrag-agent [5-bucket升序]"
    rep2 = triage.parse_pytest_output(with_checker)
    assert rep2["checker_reasons"]["5-bucket升序"] == 2


def test_render_is_actionable() -> None:
    text = triage.render_report(triage.parse_pytest_output(SAMPLE))
    assert "先看这里" in text
    assert "[2 次]" in text
    assert "完整 FAILED 列表" in text
    assert "先修根因" in text


def test_render_green_is_short() -> None:
    text = triage.render_report(triage.parse_pytest_output("5 passed in 1.0s"))
    assert "failed=0" in text
    assert "无需取证" in text
