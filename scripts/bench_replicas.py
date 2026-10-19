"""六个复刻项目的合并回归基准。

做法：扫 --root 下的 agentlisp-* 项目，逐个
  1. 用编译器重编所有 .al（--force）
  2. 跑该项目的 pytest
  3. 汇总

用法：
  python3 scripts/bench_replicas.py --root ~/products
  python3 scripts/bench_replicas.py --root ~/products --no-compile   # 只跑测试
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "compiler" / "main.rkt"
_BUNDLED = ROOT / ".racket" / "bin" / "racket"
RACKET = shutil.which("racket") or (str(_BUNDLED) if _BUNDLED.exists() else None)


def projects(root: Path) -> list[Path]:
    return sorted(p for p in root.glob("agentlisp-*") if (p / "agents").is_dir())


def compile_al(proj: Path) -> tuple[bool, str]:
    if not RACKET:
        return False, "racket 不可用"
    als = sorted((proj / "agents").glob("*.al"))
    if not als:
        return False, "没有 .al"
    outs = []
    for al in als:
        out = proj / "agents" / "dist" / (al.stem + ".py")
        out.parent.mkdir(parents=True, exist_ok=True)
        cp = subprocess.run(
            [RACKET, str(MAIN), "-i", str(al), "-o", str(out), "--force"],
            cwd=str(proj),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        if cp.returncode != 0:
            return False, f"{al.name}: {cp.stderr.strip().splitlines()[-1][:80]}"
        outs.append(out.name)
    return True, ", ".join(outs)


def clean_state(proj: Path) -> None:
    """清掉上一次跑留下的 data/ 状态。

    不清理的话基准不可重复：spec-writer 的 scan 看到上次生成的
    data/kb/01-chart-of-accounts.md，kb_missing 变空 -> 走另一条分支 -> 测试红。
    """
    data = proj / "data"
    for name in ("kb", "out", "phase.txt"):
        target = data / name
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink()


def run_tests(proj: Path, timeout: int = 180) -> tuple[bool, str]:
    # 必须给单项目超时：实测某个项目的测试能挂住（图里有回流），
    # 不设超时整个基准就跑不完，且看不到任何中间结果。
    try:
        cp = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider", "--no-cov"],
            cwd=str(proj),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"超时（>{timeout}s）"
    tail = [ln for ln in cp.stdout.strip().splitlines() if ln.strip()]
    summary = tail[-1] if tail else "(无输出)"
    return cp.returncode == 0, summary


def node_counts(proj: Path) -> str:
    """从编译产物里数节点/中断/工具，作为规模指标。"""
    src = ""
    for py in (proj / "agents" / "dist").glob("*.py"):
        src += py.read_text(encoding="utf-8", errors="replace")
    if not src:
        return "-"
    nodes = len(set(re.findall(r"def _al_node_(\w+)\(", src)))
    tools = len(set(re.findall(r"def _al_tool_(\w+)\(", src)))
    interrupts = src.count("_al.interrupt_payload(")
    return f"{nodes} 节点 / {tools} 工具 / {interrupts} 中断"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/products"))
    ap.add_argument("--no-compile", action="store_true")
    args = ap.parse_args()

    root = Path(os.path.expanduser(args.root))
    projs = projects(root)
    if not projs:
        print(f"[bench] {root} 下没有 agentlisp-* 项目", file=sys.stderr)
        return 1

    rows = []
    failed = 0
    for p in projs:
        if args.no_compile:
            ok_c, msg_c = True, "跳过"
        else:
            ok_c, msg_c = compile_al(p)
        if ok_c:
            clean_state(p)
        ok_t, msg_t = run_tests(p) if ok_c else (False, "未跑（编译失败）")
        if not (ok_c and ok_t):
            failed += 1
        rows.append((p.name, ok_c, ok_t, msg_c, msg_t, node_counts(p)))

    print(f"{'项目':<24}{'编译':<6}{'测试':<6}{'规模':<22}结果")
    print("-" * 78)
    for name, ok_c, ok_t, msg_c, msg_t, scale in rows:
        print(
            f"{name:<24}{'OK' if ok_c else 'FAIL':<6}{'OK' if ok_t else 'FAIL':<6}{scale:<22}{msg_t}"
        )
        if not ok_c:
            print(f"{'':<24}编译错误：{msg_c}")

    print("-" * 78)
    print(f"[bench] {len(rows) - failed}/{len(rows)} 项目全绿")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
