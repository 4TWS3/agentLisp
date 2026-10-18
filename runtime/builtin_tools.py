"""内置工具实现：让 `(:tools (import-builtin bash ...))` 开箱可用。

为什么需要这个模块：
  编译产物只带声明（`tools_config["import_builtins"]`），BaseHarnessV2 之前
  不会据声明建注册表 → DSL 说有 bash，跑起来却「工具未注册」。

安全边界：
  bash 这类工具能执行任意命令。真正的闸在 `constrain`（require_human_approval /
  forbidden_commands），不在这里。本模块只负责「把声明的工具真的做出来」。
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

_CMD_PARAMS: dict[str, Any] = {
    "type": "object",
    "properties": {"cmd": {"type": "string", "description": "Shell command"}},
    "required": ["cmd"],
}

# 基础实现：名字 -> (描述, 参数 schema)
IMPLEMENTED: dict[str, dict[str, Any]] = {
    "bash": {
        "description": "Run a shell command and return stdout/stderr/exit_code.",
        "parameters": _CMD_PARAMS,
    },
    "read-file": {
        "description": "Read a UTF-8 text file and return its content.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    "write-back": {
        "description": "Write content to a file (creates parent dirs).",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    "patch-text": {
        "description": "Replace the first occurrence of old with new in a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
        },
    },
    "grep": {
        "description": "Search a regex in a file or directory; returns matching lines.",
        "parameters": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}},
            "required": ["pattern"],
        },
    },
}

# 别名：DSL 里存在的其它名字 -> 复用的实现。
# 为什么要有：SRS 的生产示例用的是 write-md / apply-patch-builtin / grep-builtin，
# 副作用内置工具用 git-push / curl 等。名字不同，语义是同一个动作。
ALIASES: dict[str, str] = {
    # 副作用内置工具（constrain 按这些名字判危险操作）
    "git-push": "bash",
    "wget": "bash",
    "curl": "bash",
    "scp": "bash",
    "dd": "bash",
    "chmod": "bash",
    "sudo": "bash",
    # SRS 生产示例里的名字
    "write-md": "write-back",
    "apply-patch-builtin": "patch-text",
    "grep-builtin": "grep",
}

BUILTIN_SPECS: dict[str, dict[str, Any]] = {
    **IMPLEMENTED,
    **{
        alias: {**IMPLEMENTED[target], "description": f"{alias}: alias of {target}."}
        for alias, target in ALIASES.items()
    },
}


class BuiltinToolNotFoundError(KeyError):
    """声明了未实现的内置工具。列出支持清单，不静默跳过。"""


class BuiltinToolRegistry:
    """按声明构建的内置工具注册表，满足 ToolRegistryProtocol。"""

    def __init__(self, names: list[str], *, cwd: str | None = None, timeout: float = 30.0) -> None:
        unknown = [n for n in names if n not in BUILTIN_SPECS]
        if unknown:
            raise BuiltinToolNotFoundError(
                f"未实现的内置工具 {unknown}；已支持：{sorted(BUILTIN_SPECS)}"
            )
        self._names = list(dict.fromkeys(names))  # 去重保序
        self.cwd = cwd
        self.timeout = timeout

    @classmethod
    def from_config(
        cls, tools_config: dict[str, Any] | None, **kwargs: Any
    ) -> BuiltinToolRegistry | None:
        """从编译产物里的 tools_config 建注册表；没声明内置工具则返回 None。"""
        names = list((tools_config or {}).get("import_builtins") or [])
        return cls(names, **kwargs) if names else None

    def names(self) -> list[str]:
        return list(self._names)

    def to_openai_schema(self) -> list[dict[str, Any]]:
        return [
            {"type": "function", "function": {"name": n, **BUILTIN_SPECS[n]}} for n in self._names
        ]

    async def acall(self, name: str, **kwargs: Any) -> dict[str, Any]:
        if name not in self._names:
            raise BuiltinToolNotFoundError(f"工具 {name!r} 未在 import-builtin 中声明")
        target = ALIASES.get(name, name)
        fn = getattr(self, "_" + target.replace("-", "_"))
        return await fn(**kwargs)

    # ---- 各工具实现 ----

    def _run(self, cmd: str) -> dict[str, Any]:
        # shell=True 是刻意的：这就是 bash 工具本身；模型给什么命令就跑什么。
        # 真正的闸在 constrain（require_human_approval / forbidden_commands）。
        p = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=self.cwd,
            check=False,
        )
        return {"exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}

    async def _bash(self, cmd: str = "", **_: Any) -> dict[str, Any]:
        return await asyncio.to_thread(self._run, cmd)

    async def _read_file(self, path: str = "", **_: Any) -> dict[str, Any]:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            return {"exit_code": 1, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}
        return {"exit_code": 0, "stdout": text, "stderr": ""}

    async def _write_back(self, path: str = "", content: str = "", **_: Any) -> dict[str, Any]:
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        except OSError as exc:
            return {"exit_code": 1, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}
        return {"exit_code": 0, "stdout": f"wrote {len(content)} chars to {path}", "stderr": ""}

    async def _patch_text(
        self, path: str = "", old: str = "", new: str = "", **_: Any
    ) -> dict[str, Any]:
        try:
            p = Path(path)
            text = p.read_text(encoding="utf-8")
        except OSError as exc:
            return {"exit_code": 1, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}
        if old and old not in text:
            return {"exit_code": 1, "stdout": "", "stderr": f"未找到待替换文本：{old[:60]!r}"}
        p.write_text(text.replace(old, new, 1), encoding="utf-8")
        return {"exit_code": 0, "stdout": f"patched {path}", "stderr": ""}

    async def _grep(self, pattern: str = "", path: str = ".", **_: Any) -> dict[str, Any]:
        return self._run(f"grep -rn -- {json.dumps(pattern)} {json.dumps(path)}")
