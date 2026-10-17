"""US-51：双集验证 + McNemar。"""

from __future__ import annotations

from scripts.evolver.dual_set import dual_set_gate


def test_both_sets_must_pass() -> None:
    assert dual_set_gate(0.95, 0.01, 0.95, 0.01) is True
    assert dual_set_gate(0.95, 0.01, 0.80, 0.01) is False, "holdout 通过率不够"
    assert dual_set_gate(0.95, 0.01, 0.95, 0.20) is False, "holdout p 不显著"
    assert dual_set_gate(0.80, 0.01, 0.95, 0.01) is False, "new 通过率不够"


def test_uses_same_thresholds_as_fr_evo_4() -> None:
    assert dual_set_gate(0.90, 0.049, 0.90, 0.049) is True
    assert dual_set_gate(0.899, 0.049, 0.90, 0.049) is False
