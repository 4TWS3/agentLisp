"""从自然语言需求生成 .al，编译失败就带提示重试。

回路：需求 -> LLM(目录+速查) -> .al -> 编译 -> 失败则把「原因/怎么改/例子」回喂 -> 重试

判据：一次通过率 / 平均轮数。没有评测集之前，这里只给单条需求跑通的能力。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # 脚本方式运行时仓库根不在 sys.path
MAIN = ROOT / "compiler" / "main.rkt"
CATALOG = ROOT / "docs" / "llm" / "al_catalog.json"
CHEAT = ROOT / "docs" / "llm" / "CHEATSHEET.md"

SYSTEM = """你在写 agentLisp（.al）文件。规则：
1. 只输出一个 (define-agent …) 形式，不要解释、不要 markdown 围栏。
2. 必须包含 :model / :tools / :context / :harness / :state / :workflow。
3. 节点体只能用 :body 写 Lisp，不要用 :handler。
4. 可用形式见速查；不确定就用 (hash "字段" (llm "提示词"))。
"""


def _llm(prompt: str) -> str:
    import asyncio

    from runtime.llm_client import OpenAIClient

    llm = OpenAIClient(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com/v1",
        timeout=180,
    )
    out = asyncio.run(
        llm.achat(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ]
        )
    )
    return str(out.get("content") or "")


def _extract(text: str) -> str:
    i = text.find("(define-agent")
    if i < 0:
        return ""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[i : j + 1]
    return text[i:]


def _compile(src: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "g.al"
        p.write_text(src, encoding="utf-8")
        cp = subprocess.run(
            ["racket", str(MAIN), "-i", str(p), "-o", str(Path(d) / "g.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        return cp.returncode == 0, cp.stderr


def generate(requirement: str, max_rounds: int = 3) -> tuple[str, int, str]:
    catalog = CATALOG.read_text(encoding="utf-8")[:4000]
    cheat = CHEAT.read_text(encoding="utf-8")
    prompt = f"需求：{requirement}\n\n速查：\n{cheat}\n\n完整目录（截断）：\n{catalog}"
    last = ""
    for r in range(1, max_rounds + 1):
        text = _llm(
            prompt
            if r == 1
            else (f"{prompt}\n\n上次生成的代码编译失败，错误如下：\n{last}\n\n请修正。")
        )
        src = _extract(text)
        if not src:
            last = "没有找到 (define-agent …) 形式"
            continue
        ok, err = _compile(src)
        if ok:
            return src, r, ""
        last = err[-1500:]
    return "", max_rounds, last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("requirement")
    ap.add_argument("-o", "--out", default="")
    ap.add_argument("-n", "--rounds", type=int, default=3)
    args = ap.parse_args()
    src, rounds, err = generate(args.requirement, args.rounds)
    if not src:
        print(f"[fail] {rounds} 轮未通过；最后错误：\n{err[-600:]}", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else Path(tempfile.gettempdir()) / "generated.al"
    out.write_text(src, encoding="utf-8")
    print(f"[ok] {rounds} 轮通过 -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
