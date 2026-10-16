"""Agent Lisp Runtime - Python execution engine for Scheme-defined Agent DSL."""

from __future__ import annotations

from .engine import AgentEngine
from .loader import AgentLoader
from .models import (
    Agent,
    AtomicAction,
    ExecutionContext,
    ExecutionResult,
    Step,
    Tool,
    Workflow,
)


# 同一个模块被两个发行版打包。写死字面量会让 agentlisp --version
# 在 agentlisp 2.3.1 里报 0.1.0 -- US-01 实测。优先报 agentlisp 的版本。
def _resolve_version() -> str:
    """Resolve the version from the providing distribution (agentlisp first)."""
    from importlib.metadata import PackageNotFoundError, version

    for dist in ("agentlisp", "agentlisp-runtime"):
        try:
            return version(dist)
        except PackageNotFoundError:
            continue
    return "0.1.0"


__version__ = _resolve_version()
__all__ = [
    "Agent",
    "AgentEngine",
    "AgentLoader",
    "AtomicAction",
    "ExecutionContext",
    "ExecutionResult",
    "Step",
    "Tool",
    "Workflow",
    "__version__",
]
