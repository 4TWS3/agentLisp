"""AgentLisp v2 runtime common exceptions and FeatureNotInstalledError pattern."""

from __future__ import annotations


class AgentLispError(Exception):
    """Base exception for all AgentLisp runtime errors."""


class FeatureNotInstalledError(AgentLispError):
    """Raised when an optional-dependency feature is accessed without the package installed."""

    feature: str
    install_group: str

    def __init__(self, feature: str, install_group: str, details: str = "") -> None:
        self.feature = feature
        self.install_group = install_group
        msg = (
            f"Feature '{feature}' requires optional dependency group '{install_group}'. "
            f"Install with: uv pip install 'agentlisp[{install_group}]'"
        )
        if details:
            msg += f" ({details})"
        super().__init__(msg)


class HarnessError(AgentLispError):
    pass


class CheckpointError(AgentLispError):
    pass


class ToolNotFoundError(AgentLispError):
    pass
