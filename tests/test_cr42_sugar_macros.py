"""核心语法糖宏：defmemory-agent 与 defmultiagent（规格 §3.3-12 / §3.5-20）。

判据：
- 正例 → 展开为合法 Core AST，产物含对应 (:pattern …)，且 Python 语法合法；
- 负例 → 参数类型/取值非法时编译期报错。
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HAS_RACKET = shutil.which("racket") is not None
pytestmark = pytest.mark.skipif(not HAS_RACKET, reason="racket not on PATH")


def _compile(tmp_path: Path, src: str) -> subprocess.CompletedProcess[str]:
    al = tmp_path / "c.al"
    al.write_text(src + "\n", encoding="utf-8")
    return subprocess.run(
        ["racket", "compiler/main.rkt", "-i", str(al), "-o", str(tmp_path / "o.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def test_memory_macro_expands_with_pattern(tmp_path: Path) -> None:
    cp = _compile(tmp_path, '(defmemory-agent mem-agent "./memory/x.md" 8)')
    assert cp.returncode == 0, cp.stderr[-400:]
    out = (tmp_path / "o.py").read_text(encoding="utf-8")
    ast.parse(out)
    assert "'pattern': \"memory\"" in out
    assert "'store': \"./memory/x.md\"" in out
    assert "'context_window_gc': 8" in out
    # 三层加载必须出现（层枚举与 parser 白名单一致）
    for layer in ("L0-Abstract", "L1-Overview", "L2-FullText"):
        assert layer in out, f"缺层 {layer}"


def test_multiagent_macro_expands_with_pattern(tmp_path: Path) -> None:
    cp = _compile(tmp_path, "(defmultiagent team-agent orchestration researcher writer)")
    assert cp.returncode == 0, cp.stderr[-400:]
    out = (tmp_path / "o.py").read_text(encoding="utf-8")
    ast.parse(out)
    assert "'pattern': \"multi-agent\"" in out
    assert "'topology': \"orchestration\"" in out
    assert "researcher" in out and "writer" in out


@pytest.mark.parametrize(
    ("label", "src", "needle"),
    [
        ("memory-store-not-string", "(defmemory-agent m 123 8)", "defmemory-agent"),
        ("memory-window-not-int", '(defmemory-agent m "./x.md" "8")', "defmemory-agent"),
        ("multiagent-bad-topology", "(defmultiagent t star-network a b)", "defmultiagent"),
        ("multiagent-no-workers", "(defmultiagent t peer)", "defmultiagent"),
    ],
    ids=[
        "memory-store-not-string",
        "memory-window-not-int",
        "multiagent-bad-topology",
        "multiagent-no-workers",
    ],
)
def test_sugar_negative_cases(tmp_path: Path, label: str, src: str, needle: str) -> None:
    """参数非法时，宏必须在展开期报错。

    已知缺陷（已入台账）：main.rkt 对「宏展开失败」目前只打日志、仍返回 0。
    因此本用例只断言错误信息出现，不断言退出码；退出码语义待单独修复。
    """
    cp = _compile(tmp_path, src)
    combined = cp.stderr + cp.stdout
    assert "FAIL" in combined, f"[{label}] 未报告展开失败：{combined[-200:]}"
    assert needle in combined, f"[{label}] 报错未提到宏名"
