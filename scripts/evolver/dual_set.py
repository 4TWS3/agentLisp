"""US-51：双集验证 + McNemar。复用 run_t2_bench 的 evolver_gate（不复制判断）。"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _bench_gate():
    src = Path(__file__).resolve().parents[1] / "bench" / "run_t2_bench.py"
    spec = importlib.util.spec_from_file_location("run_t2_bench_gate_mod", src)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.evolver_gate


def dual_set_gate(
    new_pass_rate: float,
    new_p: float,
    holdout_pass_rate: float,
    holdout_p: float,
    min_pass_rate: float = 0.90,
) -> bool:
    """两集都要过：pass_rate >= min 且 p < 0.05。"""
    gate = _bench_gate()
    return bool(
        gate(new_pass_rate, new_p, min_pass_rate)
        and gate(holdout_pass_rate, holdout_p, min_pass_rate)
    )
