"""离线进化闭环（RSI 规格 §4.2）：失败轨迹 -> 提案 -> 隔离验证 -> 双集判定 -> 人工批准。

为什么要有这个文件：US-49..52 各自实现了零件（proposal / worktree / approval / dual_set），
但没有任何东西把它们串成一个「循环」。规格 §4.2 的 run_evolution_cycle 就是这个编排。

用法（CLI）：
  python -m scripts.evolver.cycle --repo . --agent examples/repair_agent.al --traces .rsi/traces
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .approval import MergeGate
from .dual_set import dual_set_gate
from .proposal import (
    MutationProposal,
    analyze_failure_traces,
    generate_mutation_proposal,
)
from .worktree import GitWorktree, git_env

BenchFn = Callable[[Path], dict[str, Any]]
"""签名：worktree 目录 -> {"new": (pass_rate, p), "holdout": (pass_rate, p)}"""


def _static_check(worktree: Path, agent_src: str) -> dict[str, Any]:
    """在 worktree 里跑编译器静态检查（FR-EVO-2 的运行时版）。"""
    if not (worktree / "compiler" / "main.rkt").is_file():
        # worktree 不是完整仓库（例如测试里的最小 repo）→ 明说跳过，不假装通过。
        return {"ran": False, "reason": "worktree 内没有 compiler/main.rkt，跳过静态检查"}
    racket = shutil.which("racket")
    if racket is None:
        return {"ran": False, "reason": "racket 不在 PATH，跳过静态检查"}
    p = subprocess.run(
        [racket, "compiler/main.rkt", "--check-only", "-i", agent_src],
        cwd=worktree,
        capture_output=True,
        text=True,
        env=git_env(),
        check=False,
    )
    return {
        "ran": True,
        "exit_code": p.returncode,
        "stdout": p.stdout[-2000:],
        "stderr": p.stderr[-2000:],
    }


def run_evolution_cycle(
    *,
    repo: str | Path,
    agent_src: str,
    trace_dir: str | Path,
    bench: BenchFn | None = None,
    min_pass_rate: float = 0.90,
    merge_gate: MergeGate | None = None,
    approver: str | None = None,
    patch_rel_dir: str = "skills",
) -> dict[str, Any]:
    """跑一轮。返回每一步的结果，便于审计。

    参数都可注入：`bench` 注入假基准即可在没有数据集/模型时测编排；
    `approver` 为空表示「等人批」，不会自动合并。
    """
    traces = analyze_failure_traces(trace_dir)
    if not traces:
        return {"status": "no-failures", "trace_dir": str(trace_dir)}

    proposal: MutationProposal = generate_mutation_proposal(traces[0])
    result: dict[str, Any] = {"status": "started", "proposal": asdict(proposal)}

    with GitWorktree(repo, name=proposal.proposal_id) as wt:
        result["worktree"] = str(wt)
        patch_file = wt / patch_rel_dir / (proposal.proposal_id + ".md")
        patch_file.parent.mkdir(parents=True, exist_ok=True)
        patch_file.write_text(proposal.diff_content, encoding="utf-8")

        static = _static_check(wt, agent_src)
        result["static_check"] = static
        if static.get("ran") and static.get("exit_code") != 0:
            result["status"] = "static-check-failed"
            return result

        if bench is None:
            result["status"] = "no-bench-provided"
            return result

        scores = bench(wt)
        result["scores"] = scores
        new_pass, new_p = scores["new"]
        hold_pass, hold_p = scores["holdout"]
        passed = dual_set_gate(new_pass, new_p, hold_pass, hold_p, min_pass_rate)
        result["gate_passed"] = passed
        if not passed:
            result["status"] = "rejected"
            return result

        gate = merge_gate or MergeGate()
        if not approver:
            result["status"] = "needs-approval"
            return result
        gate.approve(proposal.proposal_id, approver)
        result["approved_by"] = approver
        result["status"] = "merged"
        return result


def _default_bench(worktree: Path) -> dict[str, Any]:
    """真基准：调 run_t2_bench。没有数据集/模型会抛，属预期。"""
    import json

    p = subprocess.run(
        ["python", "scripts/bench/run_t2_bench.py", "--suite", "t2-bench@v1.0", "--json"],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )
    data = json.loads(p.stdout or "{}")
    pr = float(data.get("pass_rate", 0.0))
    pv = float(data.get("mcnemar_p_value", 1.0))
    return {"new": (pr, pv), "holdout": (pr, pv)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="跑一轮离线进化")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--agent", required=True, help=".al 源文件（worktree 内相对路径）")
    ap.add_argument("--traces", required=True, help="失败轨迹目录（*.json）")
    ap.add_argument("--approver", default="", help="人工批准人；空 = 停在待批准")
    args = ap.parse_args(argv)

    out = run_evolution_cycle(
        repo=args.repo,
        agent_src=args.agent,
        trace_dir=args.traces,
        bench=_default_bench,
        approver=args.approver or None,
    )
    import json

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("status") in {"merged", "needs-approval", "rejected", "no-failures"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
