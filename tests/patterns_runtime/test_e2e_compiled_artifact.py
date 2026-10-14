"""端到端（用户路径）：带模式的 .al → 编译 → **在子进程里 import 产物** → 运行时真的载入模式。

设计要点（自审整改）：
  * 不改本进程的 sys.path（坑 #15 的守护测试会拦）；用子进程 + cwd=仓库根，与真实用法一致。
  * 产物自己构造配置，故实例化用 cls()（传位置参会与 super().__init__ 的关键字参数冲突）。
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

# racket 可能不在 PATH（minimal 发行版常放仓库内 .racket/bin）。
# 与 tests/test_output_drift.py 同一口径：PATH 优先，回退 .racket/bin，都没有则跳过。
_BUNDLED_RACKET = ROOT / ".racket" / "bin" / "racket"
RACKET = (
    "racket"
    if shutil.which("racket")
    else (str(_BUNDLED_RACKET) if _BUNDLED_RACKET.exists() else None)
)
HAS_RACKET = RACKET is not None


# 产物第 16 行是 `from runtime.base_harness_v2 import ...`。
# 探针脚本位于 tmp_path，故子进程的 sys.path[0] 是 tmp_path，不是仓库根。
# 用户装包（pip install agentlisp）后 `runtime` 可导入；仓库内则必须显式给 PYTHONPATH。
# 这条依赖是产物的公开合同，登记在 README「产物运行前置」一节。
def _probe_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"
    return env


pytestmark = pytest.mark.skipif(
    not HAS_RACKET, reason="racket 不可用（PATH 与 .racket/bin 均未找到）"
)

PROBE = """import importlib.util, json, pathlib, sys
p = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("e2e_out", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
cls = next(
    getattr(mod, n)
    for n in dir(mod)
    if n.endswith("Harness")
    and getattr(getattr(mod, n), "__module__", "") == mod.__name__  # 只认本模块定义的类，
)                                                                    # 否则会抓到 import 进来的基类
h = cls()
ctx = str(h.build_context())
print(json.dumps({
    "kinds": [x.kind for x in h.patterns.handlers],
    "directive": "pattern:priority" in ctx,
    # 契约 CT-PRIORITY-01 的两个具体值：参数必须真的从 :params 提升进产物 PATTERNS。
    # 只断言 directive 会漏掉「criteria 被丢、handler 用空 criteria 起来」这类回归。
    "criteria": "criteria=urgency" in ctx,
    "levels": "levels=3" in ctx,
    "events": len(h.patterns.events),
}, ensure_ascii=False))
"""


def test_e2e_compiled_artifact_loads_patterns(tmp_path: Path) -> None:
    src = tmp_path / "e2e.al"
    src.write_text('(defpriority-agent s\n  :criteria "urgency"\n  :levels 3)\n', encoding="utf-8")
    out = tmp_path / "e2e_out.py"
    assert RACKET is not None  # pytestmark 已跳过无 racket 的环境
    cp = subprocess.run(
        [RACKET, str(MAIN), "-i", str(src), "-o", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, f"编译失败 rc={cp.returncode}：{cp.stderr[-400:]}"
    assert out.is_file(), "未生成产物"

    probe = tmp_path / "probe.py"
    probe.write_text(PROBE, encoding="utf-8")
    run = subprocess.run(
        [sys.executable, str(probe), str(out)],
        cwd=str(ROOT),
        env=_probe_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert run.returncode == 0, f"产物在子进程里跑不起来 rc={run.returncode}：{run.stderr[-500:]}"
    got = json.loads(run.stdout.strip().splitlines()[-1])

    assert got["kinds"] == ["priority"], f"编译产物应自动载入 priority；实际 {got['kinds']!r}"
    assert got["directive"] is True, "模式指令应进入上下文（端到端接线）"
    # CT-PRIORITY-01：.al 里的 :criteria / :levels 必须活到运行时上下文（不是只进 prompt）。
    assert got["criteria"] is True, "契约 CT-PRIORITY-01：:criteria 必须从 .al 传到模式指令"
    assert got["levels"] is True, "契约 CT-PRIORITY-01：:levels 必须从 .al 传到模式指令"
    assert got["events"] == 0, "载入本身不应产生事件（事件只记介入）"
