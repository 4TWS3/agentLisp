"""US-52 / I6：无人工批准不得合并。"""

from __future__ import annotations

import pytest

from scripts.evolver.approval import MergeGate


def test_unapproved_cannot_merge() -> None:
    g = MergeGate()
    assert g.can_merge("p1") is False
    g.approve("p1", "alice")
    assert g.can_merge("p1") is True
    assert g.approver_of("p1") == "alice"


def test_empty_approver_is_rejected() -> None:
    g = MergeGate()
    with pytest.raises(ValueError):
        g.approve("p1", "  ")
    assert g.can_merge("p1") is False
