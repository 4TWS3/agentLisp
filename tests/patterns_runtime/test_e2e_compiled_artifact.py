"""端到端（用户路径）：带模式的 .al → 编译 → import 产物 → 运行时真的载入模式。

这是自审发现的最大缺口：此前所有运行时测试都**手工**设置 PATTERNS，
没有一条走「编译器产物 → patterns.load」这条路。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "compiler" / "main.rkt"


def test_e2e_compiled_artifact_loads_patterns(tmp_path: Path) -> None:
    src = tmp_path / "e2e.al"
    src.write_text('(defpriority-agent s\n  :criteria "urgency"\n  :levels 3)\n', encoding="utf-8")
    out = tmp_path / "e2e_out.py"
    cp = subprocess.run(
        ["racket", str(MAIN), "-i", str(src), "-o", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, f"编译失败 rc={cp.returncode}：{cp.stderr[-400:]}"
    assert out.is_file(), "未生成产物"

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("e2e_out", out)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cls = next(getattr(mod, n) for n in dir(mod) if n.endswith("Harness"))

    h = cls({}, {}, {}, {})
    assert h.patterns.handlers, "编译产物的 harness 应自动载入模式 handler（端到端接线）"
    assert [x.kind for x in h.patterns.handlers] == ["priority"], (
        f"应载入 priority；实际 {[x.kind for x in h.patterns.handlers]!r}"
    )
    assert "pattern:priority" in str(h.build_context()), "模式指令应进入上下文"
    assert h.patterns.events == [], "载入本身不应产生事件（事件只记介入）"
