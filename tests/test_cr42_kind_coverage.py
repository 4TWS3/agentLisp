"""CR-42 P-3e：21/21 模式在语言层可表达。

判据：
- 注册表恰好覆盖 21 个 kind（15 个由 V1/V2 宏产出 + 6 个由 (:pattern ...) 直接声明）；
- 无专属宏的 6 个模式（rag/a2a/reasoning/learning/resource-aware/goal-setting）可以被直接声明、
  通过编译期校验并出现在产物 self.PATTERNS 里。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HAS_RACKET = shutil.which("racket") is not None
REGISTRY = ROOT / "compiler" / "pattern_registry.rkt"

MACRO_KINDS = [
    "reflect",
    "router",
    "chain",
    "parallel",
    "planner",
    "priority",
    "decomposition",
    "fsm",
    "evaluator",
    "topic-model",
    "decomposer",
    "guardrails-safety",
    "hitl",
    "exception",
    "exploration",
]
DECLARED_KINDS = ["rag", "a2a", "reasoning", "learning", "resource-aware", "goal-setting"]
# CR-42 后续：核心语法糖宏（defmemory-agent / defmultiagent）对应的 kind
SUGAR_KINDS = ["memory", "multi-agent"]

BLOCKS = """(:model :provider "anthropic" :name "m" :system-prompt "s")
 (:tools (import-builtin bash))
 (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))
 (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
           (:verify :json-schema #t)
           (:correct :max-retries 2 :on-failure abort))
 (:pattern :kind {kind} :config (:markers ("{kind} 的语义标记")))"""


def _compile(tmp_path: Path, kind: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "c.al").write_text(
        f"(define-agent a {BLOCKS.format(kind=kind)})\n", encoding="utf-8"
    )
    return subprocess.run(
        ["racket", "compiler/main.rkt", "-i", str(tmp_path / "c.al"), "-o", str(tmp_path / "o.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


pytestmark = pytest.mark.skipif(not HAS_RACKET, reason="racket not on PATH")


def test_registry_covers_21_kinds() -> None:
    expr = (
        # as_posix()：Windows 的 C:\\... 嵌进 Racket 字符串会被当转义序列（CI 实测 \p 报错）
        '(require (file "' + REGISTRY.as_posix() + '"))'
        " (for ([k (in-list (pattern-kinds))]) (displayln k))"
    )
    cp = subprocess.run(
        ["racket", "-e", expr],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    kinds = [line.strip() for line in cp.stdout.splitlines() if line.strip()]
    # 21 个 CR-41/CR-42 模式 kind + 2 个核心语法糖 kind（memory / multi-agent）
    assert len(kinds) == 23, f"注册表 kind 数 = {len(kinds)}，应为 23：{kinds}"
    for k in MACRO_KINDS + DECLARED_KINDS + SUGAR_KINDS:
        assert k in kinds, f"缺少 kind {k}"


@pytest.mark.parametrize("kind", DECLARED_KINDS)
def test_declared_only_kind_compiles(tmp_path: Path, kind: str) -> None:
    cp = _compile(tmp_path, kind)
    assert cp.returncode == 0, f"[{kind}] 编译失败：{cp.stderr[-300:]}"
    out = (tmp_path / "o.py").read_text(encoding="utf-8")
    assert f"'pattern': \"{kind}\"" in out, f"[{kind}] 产物未含该 kind"
