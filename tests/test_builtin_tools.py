"""内置工具开箱可用（runtime/builtin_tools.py）。

判据：
  - 按声明建注册表：names / to_openai_schema 只含声明的
  - 未实现的工具名 → 构造时就报错（不静默跳过）
  - bash / read-file / write-back / patch-text 真能执行
  - BaseHarnessV2 不注入 registry 时也能自动接上（说的和做的一致）
"""

from __future__ import annotations

import asyncio

import pytest

from runtime.base_harness_v2 import BaseHarnessV2
from runtime.builtin_tools import (
    ALIASES,
    BUILTIN_SPECS,
    IMPLEMENTED,
    BuiltinToolNotFoundError,
    BuiltinToolRegistry,
)


def test_from_config_builds_only_declared() -> None:
    r = BuiltinToolRegistry.from_config({"import_builtins": ["bash", "read-file"]})
    assert r is not None
    assert r.names() == ["bash", "read-file"]
    assert [s["function"]["name"] for s in r.to_openai_schema()] == ["bash", "read-file"]


def test_from_config_returns_none_when_no_builtin() -> None:
    assert BuiltinToolRegistry.from_config({}) is None
    assert BuiltinToolRegistry.from_config({"import_builtins": []}) is None


def test_unknown_builtin_fails_loudly() -> None:
    with pytest.raises(BuiltinToolNotFoundError) as exc:
        BuiltinToolRegistry(["bash", "does-not-exist"])
    assert "does-not-exist" in str(exc.value)
    assert "bash" in str(exc.value), "报错要给出已支持的清单"


def test_bash_runs_and_returns_structured() -> None:
    r = BuiltinToolRegistry(["bash"])
    out = asyncio.run(r.acall("bash", cmd="echo hi"))
    assert out["exit_code"] == 0 and out["stdout"].strip() == "hi"


def test_file_tools_roundtrip(tmp_path) -> None:
    p = tmp_path / "a.txt"
    r = BuiltinToolRegistry(["read-file", "write-back", "patch-text"])
    assert asyncio.run(r.acall("write-back", path=str(p), content="hello world"))["exit_code"] == 0
    assert asyncio.run(r.acall("read-file", path=str(p)))["stdout"] == "hello world"
    assert (
        asyncio.run(r.acall("patch-text", path=str(p), old="world", new="there"))["exit_code"] == 0
    )
    assert asyncio.run(r.acall("read-file", path=str(p)))["stdout"] == "hello there"


def test_patch_text_missing_old_is_an_error(tmp_path) -> None:
    p = tmp_path / "a.txt"
    p.write_text("abc", encoding="utf-8")
    r = BuiltinToolRegistry(["patch-text"])
    out = asyncio.run(r.acall("patch-text", path=str(p), old="zzz", new="y"))
    assert out["exit_code"] == 1 and "未找到" in out["stderr"]


def test_harness_auto_wires_declared_builtins() -> None:
    h = BaseHarnessV2({}, {}, {"import_builtins": ["bash"]}, {})
    assert h.tool_registry is not None
    assert h.tool_registry.names() == ["bash"]


def test_harness_without_declaration_has_no_registry() -> None:
    assert BaseHarnessV2({}, {}, {}, {}).tool_registry is None


def test_specs_cover_every_implemented_tool() -> None:
    """枚举封闭：实现里的 _<name> 方法必须都在 IMPLEMENTED 里登记（别名不算实现）。"""
    impl = {
        m[1:].replace("_", "-")
        for m in dir(BuiltinToolRegistry)
        if m.startswith("_") and not m.startswith("__")
    }
    impl -= {"run", "names"}
    assert impl == set(IMPLEMENTED), f"实现与登记不一致：{impl ^ set(IMPLEMENTED)}"


def test_aliases_resolve_to_implementations() -> None:
    """别名必须指向已实现的工具，否则拼错也不报错。"""
    assert set(ALIASES) <= set(BUILTIN_SPECS)
    assert set(ALIASES.values()) <= set(IMPLEMENTED)


def test_alias_tool_runs() -> None:
    r = BuiltinToolRegistry(["grep-builtin"])
    out = asyncio.run(r.acall("grep-builtin", pattern="class BuiltinToolRegistry", path="runtime"))
    assert out["exit_code"] == 0 and "BuiltinToolRegistry" in out["stdout"]
