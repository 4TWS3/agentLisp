"""小规模 Agent 评测（RSI 用）：跑编译出来的 agent，按**可判定答案**打分。

为什么不用 τ²-bench：那套基准跑的是 host.workflow 的 RepairAgentPipeline（MockProvider），
**不跑编译产物**。进化要证明「补丁让这个 agent 变好」，就必须跑这个 agent 自己。

判分不靠 LLM 裁判：每题有确定答案（跑一条命令就能算出），避免「谁打分」引入噪声。
"""

from __future__ import annotations

import asyncio
import math
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ANSWER_RE = re.compile(r"-?\d+|true|false|是|否|[A-Za-z0-9_.-]{1,40}")


@dataclass(frozen=True)
class Task:
    id: str
    prompt: str
    expect: Callable[[str], bool]


def _num(s: str) -> int | None:
    m = re.search(r"-?\d+", s.replace(",", ""))
    return int(m.group(0)) if m else None


def _count_lines(p: Path) -> int:
    return len(p.read_text(encoding="utf-8").splitlines())


def build_tasks(root: Path) -> list[Task]:
    """题目取自仓库本身，答案可机器验算。"""
    return [
        Task(
            "line_count",
            "examples/first-agent.al 有多少行？只回答数字。",
            lambda a: _num(a) == _count_lines(root / "examples/first-agent.al"),
        ),
        Task(
            "class_count",
            "runtime/errors.py 里定义了几个 class（以 'class ' 开头的行数）？只回答数字。",
            lambda a: (
                _num(a)
                == len(
                    [
                        x
                        for x in (root / "runtime/errors.py")
                        .read_text(encoding="utf-8")
                        .splitlines()
                        if x.startswith("class ")
                    ]
                )
            ),
        ),
        Task(
            "handoff_md",
            "docs/handoff 目录下有多少个 .md 文件？只回答数字。",
            lambda a: _num(a) == len(list((root / "docs/handoff").glob("*.md"))),
        ),
        Task(
            "pyproject_version",
            "pyproject.toml 里 version 的值是什么？只回答版本号。",
            lambda a: (
                re.search(
                    r'^version = "([^"]+)"',
                    (root / "pyproject.toml").read_text(encoding="utf-8"),
                    re.M,
                )
                is not None
                and re.search(
                    r'^version = "([^"]+)"',
                    (root / "pyproject.toml").read_text(encoding="utf-8"),
                    re.M,
                ).group(1)
                in a
            ),
        ),
        Task(
            "rkt_count",
            "compiler 目录下有多少个 .rkt 文件（不含子目录）？只回答数字。",
            lambda a: _num(a) == len(list((root / "compiler").glob("*.rkt"))),
        ),
        Task(
            "test_py_count",
            "tests 目录下有多少个 .py 文件（不含子目录）？只回答数字。",
            lambda a: _num(a) == len(list((root / "tests").glob("*.py"))),
        ),
    ]


def mcnemar_p(base: dict[str, bool], patched: dict[str, bool]) -> tuple[float, int, int]:
    """精确 McNemar（二项）：返回 (p, b, c)。

    b = 基线过、补丁不过；c = 基线不过、补丁过。
    n 小的时候卡方近似不可靠，这里用精确二项。
    """
    ids = sorted(set(base) & set(patched))
    b = sum(1 for i in ids if base[i] and not patched[i])
    c = sum(1 for i in ids if not base[i] and patched[i])
    n = b + c
    if n == 0:
        return 1.0, b, c
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2 * tail), b, c


def run_eval(
    worktree: Path,
    *,
    patch_text: str | None,
    module_name: str = "first_agent",
    class_name: str = "FirstAgentHarness",
    tasks: list[Task] | None = None,
    llm: Any = None,
    max_turns: int = 3,
) -> dict[str, bool]:
    """在 worktree 里加载编译产物，逐题跑，返回 {task_id: 是否通过}。"""
    wt = Path(worktree).resolve()
    sys.path.insert(0, str(wt))
    sys.path.insert(0, str(wt / "examples" / "dist"))
    mod = __import__(module_name)
    cls = getattr(mod, class_name)

    h = cls(llm_client=llm)
    # 上限要小：模型可能一直调工具不收工（实测 30 轮 × 12 次跑十几分钟）。
    h.max_turns = max_turns
    if patch_text:
        h.model_config["system_prompt"] = (
            str(h.model_config.get("system_prompt", "")) + "\n\n" + patch_text
        )

    out: dict[str, bool] = {}
    for t in tasks or build_tasks(wt):
        trace = asyncio.run(h.run(t.prompt))
        out[t.id] = bool(t.expect(str(getattr(trace, "final_answer", "") or "")))
    return out


def paired_eval(
    worktree: Path,
    patch_text: str,
    *,
    llm_factory: Callable[[], Any],
    tasks: list[Task] | None = None,
    max_turns: int = 3,
    module_name: str = "first_agent",
    class_name: str = "FirstAgentHarness",
) -> dict[str, Any]:
    """基线 vs 补丁，同一组题，返回配对结果 + McNemar。"""
    base = run_eval(
        worktree,
        patch_text=None,
        tasks=tasks,
        llm=llm_factory(),
        max_turns=max_turns,
        module_name=module_name,
        class_name=class_name,
    )
    patched = run_eval(
        worktree,
        patch_text=patch_text,
        tasks=tasks,
        llm=llm_factory(),
        max_turns=max_turns,
        module_name=module_name,
        class_name=class_name,
    )
    p, b, c = mcnemar_p(base, patched)
    n = len(base)
    return {
        "base": base,
        "patched": patched,
        "base_pass_rate": sum(base.values()) / n if n else 0.0,
        "patched_pass_rate": sum(patched.values()) / n if n else 0.0,
        "mcnemar_p": p,
        "b_base_only": b,
        "c_patched_only": c,
        "n": n,
    }
