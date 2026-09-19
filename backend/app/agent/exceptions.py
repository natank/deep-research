from enum import StrEnum


class AgentFailureReason(StrEnum):
    INVALID_ACTION = "invalid_action"
    LIMIT_EXCEEDED = "limit_exceeded"
    PROVIDER_FAILURE = "provider_failure"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    FINISHED_WITHOUT_REPORT = "finished_without_report"


class AgentContractError(ValueError):
    """Raised when untrusted Agent or provider data violates a contract."""

    def __init__(self, reason: AgentFailureReason = AgentFailureReason.INVALID_ACTION) -> None:
        self.reason = reason
        super().__init__(reason.value)


class AgentLimitError(AgentContractError):
    """Raised when a server-owned execution limit is exhausted."""

    def __init__(self) -> None:
        super().__init__(AgentFailureReason.LIMIT_EXCEEDED)


class AgentProviderError(RuntimeError):
    """Raised when an external Agent provider operation fails."""


class AgentRunError(RuntimeError):
    """Raised when a bounded Agent run ends without a report."""

    def __init__(self, reason: AgentFailureReason) -> None:
        self.reason = reason
        super().__init__(reason.value)
