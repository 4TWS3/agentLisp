"""把生成的 Python traceback 映射回 .al 的行号。

为什么需要：产物是 Python，报错行号对不上 .al；调试时得知道是哪个节点、哪一行。

做法：产物里的节点函数名是 _al_node_<节点名>（编译器保证），
拿节点名回 .al 里找 "(节点名 :type" 所在行。不需要 srcloc，也不怕格式化差异。

用法：
  python3 scripts/al_traceback.py <traceback.txt|-> <生成.py> <源.al>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

NODE_FN = re.compile(r"def (_al_node_[A-Za-z0-9_]+)\(")
TOOL_FN = re.compile(r"def (_al_tool_[A-Za-z0-9_]+)\(")
FRAME = re.compile(r'File "([^"]+)", line (\d+), in (\w+)')


def source_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def find_decl(lines: list[str], name: str) -> int | None:
    """在 .al 里找 (name :type …) 或 (define (name …))，返回 1 基行号。"""
    pat = re.compile(r"\(\s*" + re.escape(name) + r"\s+(:type|\()")
    for i, line in enumerate(lines, start=1):
        if pat.search(line):
            return i
    return None


def name_of(fn: str) -> tuple[str, str]:
    if fn.startswith("_al_node_"):
        return "节点", fn[len("_al_node_") :]
    if fn.startswith("_al_tool_"):
        return "工具", fn[len("_al_tool_") :]
    return "函数", fn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("traceback", help="traceback 文本文件，- 表示 stdin")
    ap.add_argument("generated", type=Path, help="生成的 .py")
    ap.add_argument("source", type=Path, help=".al 源文件")
    args = ap.parse_args()

    text = (
        sys.stdin.read()
        if args.traceback == "-"
        else Path(args.traceback).read_text(encoding="utf-8", errors="replace")
    )
    gen = args.generated.resolve()
    al_lines = source_lines(args.source)

    hits = []
    for path, lineno, func in FRAME.findall(text):
        try:
            same = Path(path).resolve() == gen
        except OSError:
            same = False
        if not same:
            continue
        kind, raw = name_of(func)
        al_name = raw.replace("_", "-")
        # 编译器把节点名里的非字母数字换成下划线，回找时两种写法都试
        line = find_decl(al_lines, raw) or find_decl(al_lines, al_name)
        hits.append((kind, raw, lineno, line))

    if not hits:
        print("[al_traceback] traceback 里没有来自生成文件的帧", file=sys.stderr)
        return 1

    for kind, name, py_line, al_line in hits:
        loc = f"{args.source}:{al_line}" if al_line else f"{args.source}（未找到声明）"
        print(f"{kind} {name}：生成文件第 {py_line} 行 → {loc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
