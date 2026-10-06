r"""AgentLisp v2.0 Handoff Document Compliance Checker (stdlib zero-deps).

制度化 Handoff 文档 7 章结构 + 四硬终态锚 + 下一条顺位登记的自动化核查。
每次 Handoff 写完后、push main 前执行，保证 docs/handoff/ 所有文档结构统一。

三类核查（失败 exit=1；每类前缀严格三选一：SECTION/METADATA/ANCHOR）：
  1. SECTION · 7 章标题字节级全等（grep "^## [1-7]\. "）= 7 条，顺序严格：
     ## 1. Git 状态核验 / 2. 四硬指标 / 3. 每项交付 + 精确代码锚 /
     4. 未跑/可选验证项 / 5. 硬约束 + 34-ID VERBATIM + 外部端点 /
     6. 顺位路线图（下一条顺位） / 7. 交接人签字 + 四硬终态锚
  2. METADATA · 首屏字段齐全：文档字节 >= 20KB；含精确 CR-X 编号；含下一条顺位锚（正文 >= 300 字）
  3. ANCHOR · §7.2 四硬终态锚 6 项声明值齐全（避免 §7 只有签字无数字锚，接手无法验收）

调用（本地 CR 收尾 / CI 可选门禁）：
  python3 scripts/check_handoff_compliance.py [--handoff docs/handoff/YYYYMMDD_crXX_....md]
无 --handoff 参数时默认 = docs/handoff/ 下最新 1 份（按文件名排序取最后）。
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
HANDOFF_DIR = REPO_ROOT / "docs" / "handoff"
MIN_BYTES = 20 * 1024

SEVEN_CHAPTER_TITLES: tuple[str, ...] = (
    "Git 状态核验",
    "四硬指标",
    "每项交付",
    "未跑",
    "硬约束",
    "下",
    "交接人",
)

FOUR_HARD_ANCHOR_SUBSTRINGS: tuple[str, ...] = (
    "128 passed",
    "3 skipped",
    "1 warning",
    "All checks passed!",
    "files already formatted",
    "0 files, 0 diagnostics",
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--handoff",
        type=pathlib.Path,
        default=None,
        help="指定 handoff 文档绝对或相对路径。默认 = docs/handoff/ 最新一份。",
    )
    p.add_argument(
        "--min-bytes",
        type=int,
        default=MIN_BYTES,
        help=f"文档最小字节数阈值（默认 {MIN_BYTES}=20KB）",
    )
    return p.parse_args()


def _resolve_handoff_path(cli_path: pathlib.Path | None) -> pathlib.Path:
    if cli_path is not None:
        p = cli_path if cli_path.is_absolute() else (REPO_ROOT / cli_path).resolve()
        if not p.is_file():
            print(f"METADATA handoff 文件不存在: {p}", file=sys.stderr)
            sys.exit(1)
        return p
    if not HANDOFF_DIR.is_dir():
        print(f"METADATA handoff 目录不存在: {HANDOFF_DIR}", file=sys.stderr)
        sys.exit(1)
    files = sorted(HANDOFF_DIR.glob("*.md"))
    if not files:
        print(f"METADATA {HANDOFF_DIR} 下无 handoff Markdown 文件", file=sys.stderr)
        sys.exit(1)
    return files[-1]


def _check_seven_chapters(text: str, path: pathlib.Path) -> None:
    chapter_lines: list[str] = []
    for line in text.splitlines():
        if re.match(r"^## [1-7]\. ", line):
            chapter_lines.append(line)
    if len(chapter_lines) != 7:
        print(
            f"SECTION {path.name}: 7 章标题数 ≠ 7（实际 = {len(chapter_lines)} 条）。"
            f" 期望 7 条精确匹配 ^## [1-7].  实际 = {chapter_lines!r}",
            file=sys.stderr,
        )
        sys.exit(1)
    for idx, (line, expected_suffix) in enumerate(
        zip(chapter_lines, SEVEN_CHAPTER_TITLES, strict=True), start=1
    ):
        expected_prefix = f"## {idx}. "
        if not line.startswith(expected_prefix) or expected_suffix not in line:
            print(
                f"SECTION {path.name}: 第 {idx} 章标题字节级不匹配。"
                f" 期望前缀='{expected_prefix}' + 含子串='{expected_suffix}'。"
                f" 实际行='{line}'",
                file=sys.stderr,
            )
            sys.exit(1)


def _check_metadata(text: str, path: pathlib.Path, min_bytes: int) -> None:
    size = path.stat().st_size
    if size < min_bytes:
        print(
            f"METADATA {path.name}: 文档字节 {size} B < 阈值 {min_bytes} B（20KB）。"
            f" 内容过于单薄，请按 CR-36/37 handoff 模板补充代码锚 / 证据链 / 外部端点。",
            file=sys.stderr,
        )
        sys.exit(1)
    if not re.search(r"\bCR-\d{2,}\b", path.name + "\n" + text[:1000]):
        print(
            f"METADATA {path.name}: 文件名/首屏 1000 字内未发现 CR-XX 编号（格式 CR-<至少 2 位数字>）。"
            f" handoff 文件名应为 YYYYMMDD_crXX_<action>_handoff.md，首屏标题行应含 CR-XX 全称。",
            file=sys.stderr,
        )
        sys.exit(1)
    start = None
    end = None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^## 6\. ", line):
            start = i + 1
        elif start is not None and re.match(r"^## 7\. ", line):
            end = i
            break
    if start is None:
        print(
            f"METADATA {path.name}: 未找到 §6 顺位路线图章节（无法抽取下一条顺位）。",
            file=sys.stderr,
        )
        sys.exit(1)
    chapter6_body = "\n".join(lines[start:end] if end is not None else lines[start:])
    if len(chapter6_body.strip()) < 300:
        print(
            f"METADATA {path.name}: §6 顺位路线图正文 < 300 字（实际 {len(chapter6_body.strip())} 字）。"
            f" 必须明确列出下一条顺位候选（高优先级/中优先级/远期三档 + 每档动作 verbatim）。",
            file=sys.stderr,
        )
        sys.exit(1)


def _check_four_hard_anchors(text: str, path: pathlib.Path) -> None:
    chapter7_match = re.search(
        r"## 7\..*?(?=(?:\n## |\Z))",
        text,
        flags=re.S,
    )
    if not chapter7_match:
        print(
            f"ANCHOR {path.name}: 未找到 §7 交接人签字 + 四硬终态锚章节。",
            file=sys.stderr,
        )
        sys.exit(1)
    chapter7_text = chapter7_match.group(0)
    missing: list[str] = [s for s in FOUR_HARD_ANCHOR_SUBSTRINGS if s not in chapter7_text]
    if missing:
        print(
            f"ANCHOR {path.name}: §7.2 四硬终态锚声明缺少 {len(missing)} 个关键子串。"
            f" 缺少 = {missing!r}。应在 §7.2 表中精确写入 pytest 128 passed/3 skipped/1 warning + "
            f"ruff All checks passed! + ruff N files already formatted + IDE 0 files, 0 diagnostics 6 条。",
            file=sys.stderr,
        )
        sys.exit(1)
    if "四硬终态锚" not in chapter7_text:
        print(
            f"ANCHOR {path.name}: §7 缺少子标题「7.2 四硬终态锚」（只有签字/模板结构无数字锚，接手无精确验收依据）。",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    args = _parse_args()
    path = _resolve_handoff_path(args.handoff)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"SECTION 读取 handoff 失败: {path}（{e}）", file=sys.stderr)
        sys.exit(1)

    _check_seven_chapters(text, path)
    _check_metadata(text, path, args.min_bytes)
    _check_four_hard_anchors(text, path)

    today = datetime.date.today().isoformat()
    size_kb = path.stat().st_size / 1024
    print(
        f"HANDOFF OK [{today}] {path.name} "
        f"(size={size_kb:.1f} KB · 7 章全 · 四硬锚 6/6 · §6 顺位充足)",
    )


if __name__ == "__main__":
    main()
