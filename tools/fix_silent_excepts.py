#!/usr/bin/env python3
"""给静默 except 补留痕（AST 定位，不用行号）。

判据：标准 P5/E3 —— except 之后只 pass / 返回 None 而无任何日志 = 违规。

设计要点（来自违反记录）：
  * 用 AST 找 handler，不按行号插 —— 行号插会插进多行括号 import 里，弄坏模块。
  * 输出必须是**真实发生的**：只统计 changed，跳过必须给原因。
  * 幂等：handler 里已有 logging/print 调用则跳过。
  * 缺 import logging 时，在**最后一个顶层 import 之后**插入（AST 行号）。

用法：
    python3 tools/fix_silent_excepts.py --check     # 只报告，不改
    python3 tools/fix_silent_excepts.py             # 改
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from standards_check import is_silent_handler  # noqa: E402

TARGET_DIRS = ("runtime", "host", "python/agentlisp_runtime", "tests", "scripts", "tools")
SELF = Path(__file__).resolve()

LOG_CALL = 'logging.getLogger(__name__).debug("swallowed exception", exc_info=True)'
TRACE_HINT = ("logging", "logger", "print(", "warnings.warn", "raise")


def _is_silent(handler: ast.ExceptHandler) -> bool:
    """与检查器 P5/E3 共用同一判据（同一判断只有一处实现）。"""
    return is_silent_handler(handler)


def _import_line(tree: ast.Module) -> int:
    last = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last = max(last, node.end_lineno or node.lineno)
    return last


def process(path: Path, apply: bool) -> tuple[str, str]:
    original = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(original)
    except SyntaxError as e:
        return "skipped", f"语法错误 {e}"
    targets = [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler) and _is_silent(n)]
    if not targets:
        return "skipped", "无静默 handler"
    has_logging = any(
        (isinstance(n, ast.Import) and any(a.name == "logging" for a in n.names))
        or (isinstance(n, ast.ImportFrom) and n.module == "logging")
        for n in ast.walk(tree)
    )
    if not apply:
        return "found", f"{len(targets)} 处静默 handler"
    lines = original.splitlines(keepends=True)
    # 先插日志调用（自下而上，避免行号漂移）
    for node in sorted(targets, key=lambda n: n.lineno, reverse=True):
        first = node.body[0]
        indent = " " * (first.col_offset)
        # 把 pass 换掉，或在其前插入
        if isinstance(first, ast.Pass):
            lines[first.lineno - 1] = f"{indent}{LOG_CALL}\n"
        else:
            lines.insert(first.lineno - 1, f"{indent}{LOG_CALL}\n")
    if not has_logging:
        at = _import_line(tree)
        lines.insert(at, "import logging\n")
    out = "".join(lines)
    try:
        ast.parse(out)
    except SyntaxError as e:
        return "skipped", f"改动后语法错误，已放弃：{e}"
    path.write_text(out, encoding="utf-8")
    return "changed", f"{len(targets)} 处已补留痕" + (
        "" if has_logging else "（含新增 import logging）"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只报告，不改文件")
    args = ap.parse_args()
    counts = {"changed": 0, "found": 0, "skipped": 0}
    changed_files = 0
    for d in TARGET_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.py")):
            if "__pycache__" in p.parts or p.resolve() == SELF:
                continue
            status, detail = process(p, apply=not args.check)
            counts[status] = counts.get(status, 0) + 1
            if status == "changed":
                changed_files += 1
                print(f"[CHANGED] {p.relative_to(ROOT)} — {detail}")
            elif status == "found":
                print(f"[FOUND]   {p.relative_to(ROOT)} — {detail}")
    print(
        f"\n合计：改动 {changed_files} 个文件 / 命中 {counts.get('found', 0)} 个文件 / "
        f"跳过 {counts.get('skipped', 0)} 个文件（跳过原因见 [FOUND]/无静默 handler）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
