"""US-27：21 个 kind 的 E2E（编译 -> 子进程 import 产物 -> 断言）。

每条：显式 (:pattern :kind K :config ...) 块 -> 编译 -> 子进程跑 -> 断行为。
契约来源：docs/spec/pattern_runtime_contracts/<kind>.md。
落地 13 个断言引擎真调用的行为；声明层 8 个断言 handler 的纯函数。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "compiler" / "main.rkt"
_BUNDLED_RACKET = ROOT / ".racket" / "bin" / "racket"
RACKET = (
    "racket"
    if shutil.which("racket")
    else (str(_BUNDLED_RACKET) if _BUNDLED_RACKET.exists() else None)
)
HAS_RACKET = RACKET is not None

PROBE = """import importlib.util, json, pathlib, sys
p = pathlib.Path(sys.argv[1]); kind = sys.argv[2]; check = sys.argv[3]
spec = importlib.util.spec_from_file_location("e2e_out", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
cls = next(getattr(mod, n) for n in dir(mod) if n.endswith("Harness") and getattr(getattr(mod, n), "__module__", "") == mod.__name__)
h = cls()
rt = h.patterns
ctx = str(h.build_context())
api = rt.api(kind)
res = bool(eval(check, {"h": h, "rt": rt, "api": api, "ctx": ctx}))
print(json.dumps({"kinds": [x.kind for x in rt.handlers], "directive": ("pattern:" + kind) in ctx, "result": res}))
"""

# kind -> (config plist 片段, 行为断言表达式)
CASES = {
    "priority": (
        ':criteria "urgency" :levels 3',
        '[c["id"] for c in rt.order([{"id": "a", "urgency": 1}, {"id": "b", "urgency": 3}])] == ["b", "a"]',
    ),
    "exception": (':retries 1 :backoff "linear"', "rt.retries_cap(5) == 1"),
    "exploration": (":budget 3 :convergence 0.1", "rt.turn_budget(50) == 3"),
    "resource-aware": (':budget "low"', 'h.model_config.get("tier") == "small"'),
    "hitl": (
        ':approval-before ("bash")',
        'rt.on_tool_call({"tool_name": "bash", "args": {}})[0] is False',
    ),
    "fsm": (
        ':initial-state "idle" :states ("idle->run:start")',
        'api.transition("idle", "start") == "run"',
    ),
    "rag": (
        ':retriever "inmemory"',
        'rt.verify_observation({"answer": "x", "evidence_ids": []})[0] is False',
    ),
    "decomposer": (
        ':schema-fields ("name" "kind")',
        'rt.verify_observation({"fields": {"name": "a"}})[0] is False',
    ),
    "evaluator": (':thresholds ("0.5" "0.8")', 'rt.verify_observation({"score": 0.1})[0] is False'),
    "reflect": (':reviewer-agent "r"', 'rt.verify_observation({"reviewer": ""})[0] is False'),
    "guardrails-safety": (
        ':hooks ("constrain" "verify" "correct")',
        'rt.verify_observation({"audit": ""})[0] is False',
    ),
    "reasoning": (':technique "cot"', 'rt.verify_observation({"reasoning": ""})[0] is False'),
    "goal-setting": (':goal "g"', 'rt.verify_observation({"progress": 0.5})[0] is False'),
    "a2a": (':protocol "inmemory"', 'api.protocol() == "inmemory"'),
    "chain": (':steps ("plan" "act")', 'api.steps() == ["plan", "act"]'),
    "decomposition": (":max-depth 2", 'api.children("t", 2) == ["t.1", "t.2"]'),
    "learning": (':skill-dir ".agentlisp/skills"', 'api.skill_dir() == ".agentlisp/skills"'),
    "parallel": (':branches ("a" "b")', 'api.branches() == ["a", "b"]'),
    "planner": (":plan-size 3", "api.plan_size() == 3"),
    "router": (':routes ("deploy=>ops")', 'api.route("deploy") == "ops"'),
    "topic-model": (':processor "cluster-agent"', 'api.processor() == "cluster-agent"'),
}


def _src(agent: str, kind: str, config: str) -> str:
    return chr(10).join(
        [
            "(define-agent " + agent,
            '  (:model :provider "anthropic" :name "m" :system-prompt "s")',
            "  (:tools (import-builtin bash))",
            '  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))',
            '  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))',
            "            (:verify :json-schema #t)",
            "            (:correct :max-retries 2 :on-failure abort))",
            "  (:pattern :kind " + kind + ' :config (:markers ("m1") ' + config + ")))",
            "",
        ]
    )


def _probe_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not existing else str(ROOT) + os.pathsep + existing
    return env


@pytest.mark.skipif(not HAS_RACKET, reason="racket 不可用（PATH 与 .racket/bin 均未找到）")
@pytest.mark.parametrize("kind", sorted(CASES))
def test_e2e_kind_compiles_runs_and_asserts(kind: str, tmp_path: Path) -> None:
    config, check = CASES[kind]
    agent = "e2e_" + kind.replace("-", "_")
    src = tmp_path / "e2e.al"
    src.write_text(_src(agent, kind, config), encoding="utf-8")
    out = tmp_path / "e2e_out.py"
    assert RACKET is not None
    cp = subprocess.run(
        [RACKET, str(MAIN), "-i", str(src), "-o", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, (
        "[" + kind + "] 编译失败 rc=" + str(cp.returncode) + ": " + cp.stderr[-400:]
    )

    probe = tmp_path / "probe.py"
    probe.write_text(PROBE, encoding="utf-8")
    run = subprocess.run(
        [sys.executable, str(probe), str(out), kind, check],
        cwd=str(ROOT),
        env=_probe_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert run.returncode == 0, (
        "[" + kind + "] 产物跑不起来 rc=" + str(run.returncode) + ": " + run.stderr[-500:]
    )
    got = json.loads(run.stdout.strip().splitlines()[-1])
    assert got["kinds"] == [kind], (
        "[" + kind + "] handlers 应为 [" + kind + "]，实际 " + repr(got["kinds"])
    )
    assert got["directive"] is True, "[" + kind + "] 上下文缺 pattern:" + kind + " 指令"
    assert got["result"] is True, "[" + kind + "] 行为断言失败：" + check
