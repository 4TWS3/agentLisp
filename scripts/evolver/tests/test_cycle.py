"""离线进化闭环（RSI 规格 §4.2）：把 US-49..52 的零件串成一轮。

判据：
  - 没有失败轨迹 -> no-failures
  - 双集判定不过 -> rejected（不合并不论有没有人工批准）
  - 判定过但没人批准 -> needs-approval（I6：不得自动合并）
  - 判定过 + 有批准 -> merged，且 worktree 被清理
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.evolver.approval import MergeGate
from scripts.evolver.cycle import run_evolution_cycle


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    # 必须是**合法**的 .al：有 racket 时 cycle 会跑静态检查，
    # 写个假源码会让测试结果取决于 PATH（实测：本机红、别处绿）。
    (r / "agent.al").write_text(
        "(define-agent x\n"
        '  (:model :provider "openai" :name "m" :system-prompt "s")\n'
        "  (:tools (import-builtin bash))\n"
        '  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #f))\n'
        '  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))\n'
        "            (:verify :json-schema #t) (:correct :max-retries 1 :on-failure abort)))\n",
        encoding="utf-8",
    )
    _git(r, "init")
    _git(r, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(r, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "init")
    return r


@pytest.fixture()
def traces(tmp_path: Path) -> Path:
    d = tmp_path / "traces"
    d.mkdir()
    (d / "run1.json").write_text(
        json.dumps(
            {
                "run_id": "run1",
                "status": "failed",
                "first_error": {"stage": "constrain", "code": "BLOCKED", "message": "被拦"},
            }
        ),
        encoding="utf-8",
    )
    return d


def _bench_pass(_wt: Path, _patch: str = "", _src: str = "") -> dict:
    return {"new": (0.95, 0.01), "holdout": (0.94, 0.02)}


def _bench_fail(_wt: Path, _patch: str = "", _src: str = "") -> dict:
    return {"new": (0.50, 0.40), "holdout": (0.50, 0.40)}


def test_no_failures(tmp_path: Path, repo: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    out = run_evolution_cycle(repo=repo, agent_src="agent.al", trace_dir=empty)
    assert out["status"] == "no-failures"


def test_rejected_when_gate_fails(repo: Path, traces: Path) -> None:
    out = run_evolution_cycle(
        repo=repo, agent_src="agent.al", trace_dir=traces, bench=_bench_fail, approver="alice"
    )
    assert out["status"] == "rejected"
    assert out["gate_passed"] is False


def test_needs_approval_without_human(repo: Path, traces: Path) -> None:
    out = run_evolution_cycle(repo=repo, agent_src="agent.al", trace_dir=traces, bench=_bench_pass)
    assert out["status"] == "needs-approval", "I6：没有人工批准不得合并"


def test_merged_with_approval_and_worktree_cleaned(repo: Path, traces: Path) -> None:
    gate = MergeGate()
    out = run_evolution_cycle(
        repo=repo,
        agent_src="agent.al",
        trace_dir=traces,
        bench=_bench_pass,
        merge_gate=gate,
        approver="alice",
    )
    assert out["status"] == "merged"
    assert gate.can_merge(out["proposal"]["proposal_id"])
    assert not Path(out["worktree"]).exists(), "worktree 必须清理（FR-EVO-5）"


def test_patch_into_shared_compiler_is_rejected(repo: Path, traces: Path, monkeypatch) -> None:
    """pattern-macros 只允许在该 agent 的私有副本里改，不许动共享编译器。"""
    import scripts.evolver.cycle as cyc
    from scripts.evolver.proposal import MutationProposal

    def _bad(_trace):
        return MutationProposal(
            proposal_id="patch_x",
            target="pattern-macros",
            diff_content="(define-syntax (defbroken stx) stx)",
            evidence_trace_id="run1",
            target_path="compiler/patterns.rkt",
        )

    monkeypatch.setattr(cyc, "generate_mutation_proposal", _bad)
    out = run_evolution_cycle(
        repo=repo, agent_src="agent.al", trace_dir=traces, bench=_bench_pass, approver="alice"
    )
    assert out["status"] == "rejected-protected-path"
    assert "compiler/" in out["error"]


def test_pattern_macros_defaults_to_private_dir(repo: Path, traces: Path, monkeypatch) -> None:
    """默认落盘在 patterns/（agent 私有），不是 compiler/。"""
    import scripts.evolver.cycle as cyc
    from scripts.evolver.proposal import MutationProposal

    monkeypatch.setattr(
        cyc,
        "generate_mutation_proposal",
        lambda _t: MutationProposal(
            proposal_id="patch_y",
            target="pattern-macros",
            diff_content="x",
            evidence_trace_id="run1",
        ),
    )
    out = run_evolution_cycle(
        repo=repo, agent_src="agent.al", trace_dir=traces, bench=_bench_pass, approver="alice"
    )
    assert out["patch_path"].startswith("patterns/"), out


def test_proposal_targets_come_from_first_error_stage(repo: Path, traces: Path) -> None:
    out = run_evolution_cycle(
        repo=repo, agent_src="agent.al", trace_dir=traces, bench=_bench_pass, approver="a"
    )
    assert out["proposal"]["target"] == "skills"
    assert out["proposal"]["evidence_trace_id"] == "run1"
