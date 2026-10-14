#!/usr/bin/env python3
"""生成「21 个设计模式落地清单」：每行给代码文件:行号（证据从代码里取，不手写）。

口径（2026-10-12 复核）：21 = V1 5 个宏 + V2 16 个宏，与注册表 21 个模式 kind 一一对应
（注册表共 23 kinds = 21 + memory + multi-agent）。
  * V1：compiler/patterns.rkt（5 个手写宏）→ kind: reflection/router/chain/parallel/planner
  * V2：compiler/patterns_v2.rkt（16 个，scripts/gen_patterns_v2.py 生成）→ kind 见 KIND_OF
  * 另有 5 个规格 BNF 别名（SPEC_ALIASES）转发到 V2 实现名
每行四处证据：宏定义位置 / 注册表条目位置 / kind 是否在 pattern-kinds / 夹具文件数与首名。

退出码：0 = 21/21 齐全；1 = 有缺失（缺什么打什么）。
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# US-42：运行时口径唯一真源。清单头部必须与 README / LANDED 注释一致。
from runtime.patterns import CONTRACTED, DECLARED_ONLY, LANDED  # noqa: E402

BT = chr(96)
OUT = ROOT / "docs" / "spec" / "agentlisp_pattern_landing.md"
V1_FILE = ROOT / "compiler" / "patterns.rkt"
V2_FILE = ROOT / "compiler" / "patterns_v2.rkt"
REG = ROOT / "compiler" / "pattern_registry.rkt"
FIX_V2 = ROOT / "tests" / "patterns" / "fixtures_v2"
FIX_V1 = ROOT / "tests" / "patterns" / "fixtures"

V1_PAIRS = [
    ("defreflect-agent", "reflect"),  # 注册表里就叫 reflect（曾误写成 reflection）
    ("defrouter-agent", "router"),
    ("defchain-agent", "chain"),
    ("defparallel-agent", "parallel"),
    ("defplanner-agent", "planner"),
]


def parse_gen() -> tuple[list[dict], dict, dict]:
    tree = ast.parse((ROOT / "scripts" / "gen_patterns_v2.py").read_text(encoding="utf-8"))
    patterns: list[dict] = []
    kind_of: dict = {}
    aliases: dict = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if not isinstance(t, ast.Name):
                    continue
                if t.id == "PATTERNS":
                    # PATTERNS 里含函数调用（Sym(...) 等），literal_eval 不可用 →
                    # 用两遍正则按出现顺序配对 "key" 与 "macro"（条数必须一致，否则报错，不猜）
                    src = (ROOT / "scripts" / "gen_patterns_v2.py").read_text(encoding="utf-8")
                    block = src[src.index("PATTERNS = [") : src.index("KIND_OF = {")]
                    # 实际写法是 dict(key="…", macro="…")，不是 JSON 风格
                    keys = re.findall(r'key="([^"]+)"', block)
                    macros = re.findall(r'macro="([^"]+)"', block)
                    if len(keys) != len(macros):
                        raise SystemExit(
                            "PATTERNS 解析失败：key 数 "
                            + str(len(keys))
                            + " != macro 数 "
                            + str(len(macros))
                        )
                    # strict=True：上面已断言条数一致，这里再让语言层兜一次（ruff B905）
                    patterns = [{"key": k, "macro": m} for k, m in zip(keys, macros, strict=True)]
                elif t.id == "KIND_OF":
                    kind_of = ast.literal_eval(node.value)
                elif t.id == "SPEC_ALIASES":
                    aliases = ast.literal_eval(node.value)
    return patterns, kind_of, aliases


def macro_line(path: pathlib.Path, name: str) -> int | None:
    pat = re.compile(r"\(define-syntax \(?" + re.escape(name) + r"\b")
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if pat.search(line):
            return i
    return None


def kind_line(kind: str) -> int | None:
    pats = [
        re.compile(r"register-v2-pattern!\s+'" + re.escape(kind) + r"\b"),
        re.compile(r"registry-entry\s+'" + re.escape(kind) + r"\b"),
        re.compile(r"^\s*'" + re.escape(kind) + r"\s*$"),
    ]
    for i, line in enumerate(REG.read_text(encoding="utf-8").splitlines(), 1):
        if any(p.search(line) for p in pats):
            return i
    return None


def rel(p: pathlib.Path) -> str:
    # 必须用 POSIX 分隔符：Windows 上 str() 会给出 compiler\patterns_v2.rkt，
    # 导致清单内容与断言（compiler/patterns_v2.rkt:）不一致（CI 实测）。
    return p.relative_to(ROOT).as_posix()


def main() -> int:
    # Windows 控制台默认 cp1252：直接 print 中文会 UnicodeEncodeError（CI 实测，位置 14-22）。
    # 与本仓库其它脚本同款处置：显式把两个流切到 UTF-8。
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    patterns, kind_of, aliases = parse_gen()
    rows: list[dict] = []
    problems: list[str] = []

    for macro, kind in V1_PAIRS:
        ln = macro_line(V1_FILE, macro)
        rl = kind_line(kind)
        fx = sorted(p.name for p in FIX_V1.glob("*" + macro.split("-")[0].replace("def", "") + "*"))
        if ln is None:
            problems.append("V1 宏缺定义：" + macro)
        if rl is None:
            problems.append("注册表缺 kind：" + kind)
        rows.append(
            {
                "gen": "V1",
                "macro": macro,
                "kind": kind,
                "site": (rel(V1_FILE) + ":" + str(ln)) if ln else "—",
                "reg": (rel(REG) + ":" + str(rl)) if rl else "—",
                "fx": (str(len(fx)) + " 个（" + fx[0] + "）") if fx else "—",
            }
        )

    for p in patterns:
        macro = p.get("macro", "?")
        key = p.get("key", "")
        kind = kind_of.get(key)
        ln = macro_line(V2_FILE, macro)
        rl = kind_line(kind) if kind else None
        fx = sorted(x.name for x in FIX_V2.glob(key + "*.al"))
        if ln is None:
            problems.append("V2 宏缺定义：" + macro)
        if not kind:
            problems.append("V2 模式缺 kind 映射：" + key)
        elif rl is None:
            problems.append("注册表缺 kind：" + kind)
        if not fx:
            problems.append("V2 夹具缺失：" + key + "*.al")
        rows.append(
            {
                "gen": "V2",
                "macro": macro,
                "kind": kind or "—",
                "site": (rel(V2_FILE) + ":" + str(ln)) if ln else "—",
                "reg": (rel(REG) + ":" + str(rl)) if rl else "—",
                "fx": (str(len(fx)) + " 个（" + fx[0] + "）") if fx else "—",
            }
        )

    ok = sum(1 for r in rows if r["site"] != "—" and r["reg"] != "—")
    L = [
        "# 21 个设计模式落地清单（脚本从代码生成，勿手改）",
        "",
        "> 重新生成："
        + BT
        + "python3 scripts/pattern_landing_report.py"
        + BT
        + "（判据：rc=0 表示 21/21 齐全）。",
        "> 口径：21 = V1 5 个 + V2 16 个，与注册表 21 个模式 kind 一一对应（注册表共 23 = 21 + memory + multi-agent）。",
        "> 运行时口径（唯一真源 runtime/patterns/__init__.py）："
        + f"契约 {len(CONTRACTED)} / 落地 {len(LANDED)} / 声明层 {len(DECLARED_ONLY)}"
        + "。核对脚本 scripts/check_pattern_consistency.py。",
        "> 每行的「位置」是 " + BT + "文件:行号" + BT + "，可直接跳转核对。",
        "",
        "| # | 代 | 模式（宏） | kind | 宏定义位置 | 注册表条目 | 夹具 |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        L.append(
            "| "
            + str(i)
            + " | "
            + r["gen"]
            + " | "
            + BT
            + r["macro"]
            + BT
            + " | "
            + BT
            + str(r["kind"])
            + BT
            + " | "
            + BT
            + r["site"]
            + BT
            + " | "
            + BT
            + r["reg"]
            + BT
            + " | "
            + r["fx"]
            + " |"
        )
    L += [
        "",
        "合计：**"
        + str(ok)
        + "/"
        + str(len(rows))
        + "** 个模式同时具备「宏定义 + 注册表 kind 条目」；",
        "V2 每个模式另有 3 个场景夹具（HC / GENERIC / REVERSE），共 "
        + str(len(patterns) * 3)
        + " 个。",
        "",
        "## 规格 BNF 别名（5 个，转发到 V2 实现名）",
        "",
    ]
    for a, b in sorted(aliases.items()):
        ln = macro_line(V2_FILE, a)
        L.append(
            "- "
            + BT
            + a
            + BT
            + " → "
            + BT
            + b
            + BT
            + "（宏定义 "
            + rel(V2_FILE)
            + ":"
            + str(ln)
            + "）"
        )
    L.append("")
    # newline="\n"：Windows 上 write_text 会把 \n 翻成 CRLF，导致生成物与仓库版逐字节不一致
    OUT.write_text("\n".join(L), encoding="utf-8", newline="\n")
    print("已写出 " + rel(OUT) + "：" + str(ok) + "/" + str(len(rows)) + " 齐全")
    for p in problems:
        print("  缺: " + p)
    return 0 if (not problems and ok == len(rows) and len(rows) == 21) else 1


if __name__ == "__main__":
    raise SystemExit(main())
