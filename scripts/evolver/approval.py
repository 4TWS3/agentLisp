"""US-52 / I6：无人工批准不得合并。"""

from __future__ import annotations


class MergeGate:
    def __init__(self) -> None:
        self._approved: dict[str, str] = {}

    def approve(self, proposal_id: str, approver: str) -> None:
        if not approver.strip():
            raise ValueError("批准人不能为空（人工批准必须有名字）")
        self._approved[proposal_id] = approver

    def can_merge(self, proposal_id: str) -> bool:
        return proposal_id in self._approved

    def approver_of(self, proposal_id: str) -> str | None:
        return self._approved.get(proposal_id)
