"""Agent Loader - loads agent definitions from JSON/YAML/Scheme sources."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Union

import yaml

from .models import (
    ActionType,
    Agent,
    AtomicAction,
    Step,
    Tool,
    Workflow,
)


class AgentLoader:
    @staticmethod
    def _normalize_action(action: dict[str, Any] | AtomicAction | Any) -> AtomicAction | Any:
        if isinstance(action, AtomicAction):
            return action
        if isinstance(action, dict):
            kind = action.get("type")
            if kind in {None, ActionType.ATOMIC, "atomic"}:
                return AtomicAction(
                    name=action.get("name", ""),
                    target=action.get("target", ""),
                    method=action.get("method", ""),
                    params=list(action.get("params", [])),
                    type=ActionType.ATOMIC,
                )
            return action
        return action

    @classmethod
    def _build_step(cls, step_data: dict[str, Any]) -> Step:
        normalized = dict(step_data)
        if "action" in normalized:
            normalized["action"] = cls._normalize_action(normalized["action"])
        return Step(**normalized)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Agent:
        tools = [Tool(**t) for t in data.get("tools", [])]
        workflows = [
            Workflow(
                name=wf["name"],
                triggers=wf.get("triggers", []),
                steps=[cls._build_step(s) for s in wf.get("steps", [])],
            )
            for wf in data.get("workflows", [])
        ]
        return Agent(
            name=data["name"],
            purpose=data.get("purpose", ""),
            tools=tools,
            workflows=workflows,
        )

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> Agent:
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> Agent:
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_scheme(
        cls,
        path: Union[str, Path],
        racket_exe: str = "racket",
        scheme_root: Union[str, Path, None] = None,
    ) -> Agent:
        path = Path(path)
        script_dir = path.parent
        script = f"""
#lang racket/base
(require json
         racket/runtime-path
         (file "{path.name}"))
(require (lib "agent-dsl/reader.rkt"))
(display (jsexpr->string (serialize-agent {cls._infer_agent_name(path)})))
"""
        tmp_script = script_dir / "_agent_export_tmp.rkt"
        tmp_script.write_text(script, encoding="utf-8")

        try:
            env_cmd: list[str] = [racket_exe, str(tmp_script)]
            cwd = Path(scheme_root) if scheme_root else script_dir
            result = subprocess.run(
                env_cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Racket execution failed (exit {result.returncode}):\n"
                    f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
                )
            data = json.loads(result.stdout.strip())
            return cls.from_dict(data)
        finally:
            if tmp_script.exists():
                tmp_script.unlink()

    @staticmethod
    def _infer_agent_name(path: Path) -> str:
        stem = path.stem
        if "-" in stem:
            parts = stem.split("-")
            return "".join(p for p in parts)
        return stem
