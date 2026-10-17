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


class DurableExecutionUnavailableError(AgentLispError):
    """持久化执行不可用（Temporal 只有骨架）。

    为什么单独一类：它和「依赖没装」不同 —— 依赖装了也不能用。
    调用方需要能区分「 degraded 但不丢数据」和「一重启就丢」。
    """


class HarnessError(AgentLispError):
    pass


class CheckpointError(AgentLispError):
    pass


class ToolNotFoundError(AgentLispError):
    pass
