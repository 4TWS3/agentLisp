"""define-tool 的工具体也能用 Lisp 写（模型 B 的最后一块）。

判据：
  1. :body 编译成 _al_tool_<名> 函数，并注册进 TOOL_BODIES；
  2. al_tools.from_harness 按声明生成 schema、按名字分发；
  3. 不写 :body 的工具仍可声明（交给外部注册表）；
  4. inputs 必须是真 dict 列表（曾经是字符串，运行时 TypeError）。
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "compiler" / "main.rkt"
_BUNDLED = ROOT / ".racket" / "bin" / "racket"
RACKET = "racket" if shutil.which("racket") else (str(_BUNDLED) if _BUNDLED.exists() else None)

pytestmark = pytest.mark.skipif(not RACKET, reason="racket 不可用")

SRC = """(define-agent tool-demo
  (:model :provider "openai" :name "m" :system-prompt "s")
  (:tools (import-builtin read-file)
          (define-tool add ((a int) (b int)) ((sum int))
            :body (hash "sum" (+ a b)))
          (define-tool declared_only ((q str)) ((r str))))
  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #f))
  (:state :fields ((x :type str)))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #f :linter-check #f :test-runner "")
            (:correct :max-retries 1 :on-failure abort)))
"""


def _build(tmp_path: Path):
    p = tmp_path / "c.al"
    p.write_text(SRC, encoding="utf-8")
    out = tmp_path / "o.py"
    cp = subprocess.run(
        [RACKET, str(MAIN), "-i", str(p), "-o", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr[-800:]
    spec = importlib.util.spec_from_file_location("tool_demo_" + tmp_path.name, out)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, out


def test_tool_body_compiles_to_function(tmp_path: Path) -> None:
    mod, out = _build(tmp_path)
    src = out.read_text(encoding="utf-8")
    assert "def _al_tool_add(**kwargs):" in src
    # 指纹字段用双引号格式化，别断言单引号
    assert '"add": _al_tool_add' in src and "self.TOOL_BODIES: Dict[str, Any] =" in src
    h = mod.ToolDemoHarness(llm_client=None)
    assert list(h.TOOL_BODIES) == ["add"]


def test_registry_dispatches_to_dsl_body(tmp_path: Path) -> None:
    import asyncio

    from runtime.al_tools import from_harness

    mod, _ = _build(tmp_path)
    h = mod.ToolDemoHarness(llm_client=None)
    reg = from_harness(h)
    assert reg is not None
    assert asyncio.run(reg.acall("add", a=2, b=3)) == {"sum": 5}


def test_inputs_are_real_dicts_not_strings(tmp_path: Path) -> None:
    """曾经把 inputs 包成字符串列表，运行期 schema 生成直接 TypeError。"""
    from runtime.al_tools import from_harness

    mod, _ = _build(tmp_path)
    h = mod.ToolDemoHarness(llm_client=None)
    for t in h.tools_config["define_tools"]:
        for kv in t["inputs"]:
            assert isinstance(kv, dict), (t["name"], kv)
    reg = from_harness(h)
    assert reg is not None
    schema = {s["function"]["name"]: s for s in reg.to_openai_schema()}
    assert schema["add"]["function"]["parameters"]["properties"]["a"]["type"] == "integer"
    assert schema["add"]["function"]["parameters"]["required"] == ["a", "b"]


def test_declared_only_tool_has_no_body(tmp_path: Path) -> None:
    mod, _ = _build(tmp_path)
    h = mod.ToolDemoHarness(llm_client=None)
    assert "declared_only" not in h.TOOL_BODIES
    names = [t["name"] for t in h.tools_config["define_tools"]]
    assert "declared_only" in names


def test_unknown_tool_is_loud(tmp_path: Path) -> None:
    import asyncio

    from runtime.al_tools import from_harness

    mod, _ = _build(tmp_path)
    h = mod.ToolDemoHarness(llm_client=None)
    reg = from_harness(h)
    assert reg is not None
    with pytest.raises(KeyError):
        asyncio.run(reg.acall("declared_only", q="x"))
