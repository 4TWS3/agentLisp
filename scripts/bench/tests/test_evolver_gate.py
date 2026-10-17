"""FR-EVO-4（US-45）：补丁评估门槛。

判据：pass_rate >= min_pass_rate 且 mcnemar_p_value < 0.05。
本文件位置即 SRS 指定的 scripts/bench/tests/test_evolver_gate.py。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "scripts" / "bench" / "run_t2_bench.py"


def _gate():
    spec = importlib.util.spec_from_file_location("run_t2_bench_gate_mod", SRC)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.evolver_gate


def test_gate_requires_both_conditions() -> None:
    gate = _gate()
    assert gate(0.95, 0.01) is True
    assert gate(0.95, 0.20) is False, "p 不显著不得通过"
    assert gate(0.80, 0.01) is False, "通过率不够不得通过"
    assert gate(0.80, 0.20) is False


def test_default_min_pass_rate_is_090() -> None:
    gate = _gate()
    assert gate(0.90, 0.049) is True
    assert gate(0.899, 0.049) is False


def test_p_exactly_005_is_not_significant() -> None:
    """p 必须严格小于 0.05（等于不算）。"""
    gate = _gate()
    assert gate(0.99, 0.05) is False
