"""生成 agentLisp 的机器可读目录（让 AI 查得到语言特性）。

设计：
- 目录从**编译器源码**提取，不手写 —— 编译器新增形式而目录没更新时，--check 失败。
- 输出 docs/llm/al_catalog.json，供提示词 / 工具 / 文档共用。

用法：
  python3 scripts/gen_al_catalog.py            # 写文件
  python3 scripts/gen_al_catalog.py --check    # 只校验，漂移则 exit 1
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPILER = ROOT / "compiler" / "agentlisp_compiler.rkt"
CHECKER = ROOT / "compiler" / "checker.rkt"
LISP = ROOT / "compiler" / "lisp_py.rkt"
OUT = ROOT / "docs" / "llm" / "al_catalog.json"


def _enum(src: str, name: str) -> list[str]:
    # 定义处可能有多余空格（checker.rkt 用对齐写法：PROVIDER-ENUM          '(…)
    m = re.search(rf"\(define\s+{re.escape(name)}\s+'\(", src)
    if not m:
        raise SystemExit(f"目录生成失败：编译器里找不到 {name}")
    tail = src[m.end() :]
    depth = 1
    out = []
    cur = []
    for ch in tail:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        if depth == 1 and ch.isspace():
            if cur:
                out.append("".join(cur))
                cur = []
            continue
        if depth == 1 and ch in "'":
            continue
        cur.append(ch)
    if cur:
        out.append("".join(cur))
    return [x.strip().strip('"') for x in out if x.strip()]


def _blocks(src: str) -> list[str]:
    found = sorted(set(re.findall(r"tag ':([a-z]+)\)", src)))
    return [":" + b for b in found]


def _lisp_core(src: str) -> dict[str, list[str]]:
    """从 lisp_py.rkt 的 core-fn 表提取符号 -> Python 目标。"""
    m = re.search(r"\(define \(core-fn sym\)(.*?)\n\n", src, re.S)
    if not m:
        raise SystemExit("目录生成失败：lisp_py.rkt 里找不到 core-fn")
    table: dict[str, list[str]] = {}
    pattern = r'\[\(([^)]+)\)\s+"([^"]+)"\]'
    for syms, target in re.findall(pattern, m.group(1)):
        for s in syms.split():
            table.setdefault(target, []).append(s)
    return table


def build() -> dict:
    src = COMPILER.read_text(encoding="utf-8")
    # 部分枚举定义在 checker.rkt（单一事实来源），合并后再提取
    src = src + "\n" + CHECKER.read_text(encoding="utf-8")
    lsrc = LISP.read_text(encoding="utf-8")
    return {
        "version": 1,
        "source": "compiler/agentlisp_compiler.rkt",
        "blocks": sorted(
            set(_blocks(src))
            | {
                ":model",
                ":context",
                ":tools",
                ":harness",
                ":state",
                ":workflow",
                ":multiagent",
                ":pattern",
                ":evolution",
                ":lisp",
            }
        ),
        "enums": {
            "workflow_node_type": _enum(src, "WORKFLOW-NODE-TYPES"),
            "workflow_topology": _enum(src, "WORKFLOW-TOPOLOGY-ENUM"),
            "workflow_effect": _enum(src, "WORKFLOW-EFFECT-ENUM"),
            "state_type": _enum(src, "STATE-TYPE-ENUM"),
            "state_reducer": _enum(src, "STATE-REDUCER-ENUM"),
            "provider": _enum(src, "PROVIDER-ENUM"),
            "memory_layer": _enum(src, "MEMORY-LAYER-ENUM"),
        },
        "state_reducer_types": {
            "merge": ["dict"],
            "append": ["list"],
            "sum": ["int", "float"],
        },
        "lisp_core": {k: sorted(v) for k, v in _lisp_core(lsrc).items()},
        "lisp_special_forms": [
            "if",
            "cond",
            "let",
            "let*",
            "begin",
            "and",
            "or",
            "not",
            "lambda",
            "quote",
        ],
        "notes": [
            "节点体用 :body 写 Lisp，编译器发射 _al_node_<名> 函数",
            ":handler 是逃逸口，指向外部 Python 函数",
            '完备性靠 (py/call "模块.函数" …) 宿主互操作',
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验，不写文件")
    args = ap.parse_args()
    data = build()
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT.is_file():
            print(f"[FAIL] 目录不存在：{OUT}", file=sys.stderr)
            return 1
        if OUT.read_text(encoding="utf-8") != text:
            print(
                "[FAIL] 目录与编译器漂移：跑 python3 scripts/gen_al_catalog.py 重新生成",
                file=sys.stderr,
            )
            return 1
        print("[OK] 目录与编译器一致")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"[OK] 写入 {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
