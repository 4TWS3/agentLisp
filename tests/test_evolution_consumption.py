"""US-46 / P2-3：:evolution 契约的运行时消费点。

判据：产物 EVOLUTION 至少被一个运行时可观测点读取（此前全仓零引用）。
本测试：编译带 / 不带 :evolution 的 .al，在子进程实例化产物，断言 harness.evolution。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "compiler" / "main.rkt"
_BUNDLED = ROOT / ".racket" / "bin" / "racket"
RACKET = "racket" if shutil.which("racket") else (str(_BUNDLED) if _BUNDLED.exists() else None)

pytestmark = pytest.mark.skipif(not RACKET, reason="racket 不可用（PATH 与 .racket/bin 均未找到）")

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

PROBE = """import importlib.util, json, pathlib, sys
p = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("evo", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
cls = next(getattr(mod, n) for n in dir(mod) if n.endswith("Harness") and getattr(getattr(mod, n), "__module__", "") == mod.__name__)
h = cls()
evo = getattr(h, "evolution", "MISSING")
print(json.dumps({
    "has": isinstance(evo, dict),
    "is_none": evo is None,
    "targets": (evo or {}).get("mutation_targets") if isinstance(evo, dict) else None,
}))
"""


def _compile(tmp_path: Path, extra: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "c.al").write_text(BASE.format(extra=extra), encoding="utf-8")
    assert RACKET is not None
    return subprocess.run(
        [RACKET, str(MAIN), "-i", str(tmp_path / "c.al"), "-o", str(tmp_path / "o.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def _probe(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    (tmp_path / "p.py").write_text(PROBE, encoding="utf-8")
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not existing else str(ROOT) + os.pathsep + existing
    return subprocess.run(
        [sys.executable, str(tmp_path / "p.py"), str(tmp_path / "o.py")],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def test_harness_reads_evolution_contract(tmp_path: Path) -> None:
    """带 :evolution 块 -> harness.evolution 是 dict，且带三键内容。"""
    cp = _compile(tmp_path, GOOD)
    assert cp.returncode == 0, cp.stderr[-400:]
    run = _probe(tmp_path)
    assert run.returncode == 0, run.stderr[-500:]
    got = json.loads(run.stdout.strip().splitlines()[-1])
    assert got["has"] is True, "运行期未读取 EVOLUTION（契约空转）"
    assert got["targets"] == [":pattern-macros", ":skills"]


def test_harness_without_evolution_is_none(tmp_path: Path) -> None:
    """无 :evolution 块 -> harness.evolution is None（显式，不静默丢）。"""
    cp = _compile(tmp_path, "")
    assert cp.returncode == 0, cp.stderr[-400:]
    run = _probe(tmp_path)
    assert run.returncode == 0, run.stderr[-500:]
    got = json.loads(run.stdout.strip().splitlines()[-1])
    assert got["is_none"] is True
