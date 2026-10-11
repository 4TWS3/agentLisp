"""RSI 演进契约 §5.1：(:evolution …) 的语言层支持（正负用例）。

判据：
- 合法块 → 产物 self.EVOLUTION 带三块内容，且 Python 语法合法；
- 无块 → self.EVOLUTION = None；
- 未知突变目标 / 未知不变量 / 重复块 → 编译期 parse 报错；
- 缺不变量 / 阈值越界 → checker 报 ERR_EVOLUTION_CONFIG。
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HAS_RACKET = shutil.which("racket") is not None

BASE = """(define-agent evo-agent
  (:model :provider "anthropic" :name "m" :system-prompt "s")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #t)
            (:correct :max-retries 2 :on-failure abort))
  {extra})
"""
GOOD = """(:evolution (:mutation-targets :pattern-macros :skills)
              (:immutable-invariants :kv-alignment :workspace-root :forbidden-commands)
              (:verifier-gate "t2-bench@v1.0" :min-pass-rate 0.90 :mcnemar-p-threshold 0.05))"""

pytestmark = pytest.mark.skipif(not HAS_RACKET, reason="racket not on PATH")


def _compile(tmp_path: Path, extra: str) -> subprocess.CompletedProcess[str]:
    al = tmp_path / "c.al"
    al.write_text(BASE.format(extra=extra), encoding="utf-8")
    return subprocess.run(
        ["racket", "compiler/main.rkt", "-i", str(al), "-o", str(tmp_path / "o.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_evolution_block_emits_dict(tmp_path: Path) -> None:
    cp = _compile(tmp_path, GOOD)
    assert cp.returncode == 0, cp.stderr[-400:]
    out = (tmp_path / "o.py").read_text(encoding="utf-8")
    ast.parse(out)
    assert "self.EVOLUTION" in out
    for token in (
        ":pattern-macros",
        ":skills",
        ":kv-alignment",
        ":workspace-root",
        ":forbidden-commands",
        "t2-bench@v1.0",
        "0.9",
        "0.05",
    ):
        assert token in out, f"产物 EVOLUTION 缺 {token}"


def test_without_evolution_block_emits_none(tmp_path: Path) -> None:
    cp = _compile(tmp_path, "")
    assert cp.returncode == 0, cp.stderr[-400:]
    out = (tmp_path / "o.py").read_text(encoding="utf-8")
    assert "self.EVOLUTION: Dict[str, Any] = None" in out


@pytest.mark.parametrize(
    ("label", "extra", "needle"),
    [
        (
            "unknown-target",
            '(:evolution (:mutation-targets :self-modify) (:immutable-invariants :kv-alignment :workspace-root :forbidden-commands) (:verifier-gate "g" :min-pass-rate 0.9 :mcnemar-p-threshold 0.05))',
            "未知突变目标",
        ),
        (
            "unknown-invariant",
            '(:evolution (:mutation-targets :skills) (:immutable-invariants :kv-alignment :workspace-root :forbidden-commands :extra-lock) (:verifier-gate "g" :min-pass-rate 0.9 :mcnemar-p-threshold 0.05))',
            "未知不变量",
        ),
        (
            "missing-invariant",
            '(:evolution (:mutation-targets :skills) (:immutable-invariants :kv-alignment) (:verifier-gate "g" :min-pass-rate 0.9 :mcnemar-p-threshold 0.05))',
            "ERR_EVOLUTION_CONFIG",
        ),
        (
            "rate-out-of-range",
            '(:evolution (:mutation-targets :skills) (:immutable-invariants :kv-alignment :workspace-root :forbidden-commands) (:verifier-gate "g" :min-pass-rate 1.5 :mcnemar-p-threshold 0.05))',
            "ERR_EVOLUTION_CONFIG",
        ),
        (
            "pvalue-out-of-range",
            '(:evolution (:mutation-targets :skills) (:immutable-invariants :kv-alignment :workspace-root :forbidden-commands) (:verifier-gate "g" :min-pass-rate 0.9 :mcnemar-p-threshold 0.0))',
            "ERR_EVOLUTION_CONFIG",
        ),
        ("duplicate-block", GOOD + "\n  " + GOOD, ":evolution 块重复"),
    ],
    ids=[
        "unknown-target",
        "unknown-invariant",
        "missing-invariant",
        "rate-out-of-range",
        "pvalue-out-of-range",
        "duplicate-block",
    ],
)
def test_evolution_negative_cases(tmp_path: Path, label: str, extra: str, needle: str) -> None:
    cp = _compile(tmp_path, extra)
    assert cp.returncode != 0, f"[{label}] 应当编译失败"
    assert needle in (cp.stderr + cp.stdout), f"[{label}] 报错未含 {needle}"
