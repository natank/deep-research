from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agent.exceptions import AgentFailureReason, AgentLimitError
from app.agent.limits import MAX_INVALID_ACTIONS, MAX_QUERY_LENGTH, MAX_STORED_QUERIES
from app.research.schemas import ExecutionLimits, ResearchContext
from app.searcher.schemas import SourceArticle
from app.writer.schemas import Report

SOURCE_ID_PATTERN = r"^src_[a-z0-9][a-z0-9_-]{0,63}$"
MAX_SOURCE_TITLE_LENGTH = 300
MAX_SOURCE_URL_LENGTH = 2_000
MAX_SOURCE_CONTENT_LENGTH = 4_000


class AgentOperation(StrEnum):
    SEARCH = "search"
    INSPECT_SOURCE = "inspect_source"
    REVISE_PLAN = "revise_plan"
    WRITE_REPORT = "write_report"
    FINISH = "finish"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchAction(_StrictModel):
    operation: Literal[AgentOperation.SEARCH]
    query: str = Field(min_length=1, max_length=MAX_QUERY_LENGTH)


class InspectSourceAction(_StrictModel):
    operation: Literal[AgentOperation.INSPECT_SOURCE]
    source_id: str = Field(pattern=SOURCE_ID_PATTERN)


class RevisePlanAction(_StrictModel):
    operation: Literal[AgentOperation.REVISE_PLAN]
    queries: list[str] = Field(min_length=1, max_length=MAX_STORED_QUERIES)


class WriteReportAction(_StrictModel):
    operation: Literal[AgentOperation.WRITE_REPORT]


class FinishAction(_StrictModel):
    operation: Literal[AgentOperation.FINISH]
    reason: AgentFailureReason = AgentFailureReason.FINISHED_WITHOUT_REPORT


AgentAction = Annotated[
    SearchAction
    | InspectSourceAction
    | RevisePlanAction
    | WriteReportAction
    | FinishAction,
    Field(discriminator="operation"),
]


class SourceEnvelope(_StrictModel):
    source_id: str = Field(pattern=SOURCE_ID_PATTERN)
    title: str = Field(max_length=MAX_SOURCE_TITLE_LENGTH)
    url: str = Field(max_length=MAX_SOURCE_URL_LENGTH)
    content: str = Field(max_length=MAX_SOURCE_CONTENT_LENGTH)
    score: float

    @classmethod
    def from_article(cls, source_id: str, article: SourceArticle) -> "SourceEnvelope":
        return cls(
            source_id=source_id,
            title=article.title[:MAX_SOURCE_TITLE_LENGTH],
            url=article.url[:MAX_SOURCE_URL_LENGTH],
            content=article.content[:MAX_SOURCE_CONTENT_LENGTH],
            score=article.score,
        )


class SearchResult(_StrictModel):
    operation: Literal[AgentOperation.SEARCH]
    sources: list[SourceEnvelope] = Field(max_length=8)


class InspectSourceResult(_StrictModel):
    operation: Literal[AgentOperation.INSPECT_SOURCE]
    source: SourceEnvelope


class RevisedPlanResult(_StrictModel):
    operation: Literal[AgentOperation.REVISE_PLAN]
    queries: list[str] = Field(max_length=MAX_STORED_QUERIES)


class ReportResult(_StrictModel):
    operation: Literal[AgentOperation.WRITE_REPORT]
    report: Report


class FinishResult(_StrictModel):
    operation: Literal[AgentOperation.FINISH]
    outcome: "AgentTerminalOutcome"


class AgentTerminalStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class AgentTerminalOutcome(_StrictModel):
    status: AgentTerminalStatus
    reason: AgentFailureReason | None = None
    report: Report | None = None

    @classmethod
    def success(cls, report: Report) -> "AgentTerminalOutcome":
        return cls(status=AgentTerminalStatus.SUCCESS, report=report)

    @classmethod
    def failure(cls, reason: AgentFailureReason) -> "AgentTerminalOutcome":
        return cls(status=AgentTerminalStatus.FAILURE, reason=reason)


class AgentExecutionState(_StrictModel):
    context: ResearchContext
    limits: ExecutionLimits = Field(default_factory=ExecutionLimits)
    queries: list[str] = Field(default_factory=list, max_length=MAX_STORED_QUERIES)
    revision_count: int = Field(default=0, ge=0)
    sources: list[SourceEnvelope] = Field(default_factory=list, max_length=8)
    iterations: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    searches: int = Field(default=0, ge=0)
    source_count: int = Field(default=0, ge=0)
    report_attempts: int = Field(default=0, ge=0)
    invalid_actions: int = Field(default=0, ge=0)
    retry_counts: dict[AgentOperation, int] = Field(default_factory=dict)
    terminal_outcome: AgentTerminalOutcome | None = None

    def ensure_active(self) -> None:
        if self.terminal_outcome is not None:
            raise AgentLimitError

    def record_invalid_action(self) -> None:
        self.ensure_active()
        self.invalid_actions += 1
        if self.invalid_actions >= MAX_INVALID_ACTIONS:
            self.terminal_outcome = AgentTerminalOutcome.failure(
                AgentFailureReason.INVALID_ACTION
            )

    def finish_without_report(self) -> AgentTerminalOutcome:
        self.ensure_active()
        self.terminal_outcome = AgentTerminalOutcome.failure(
            AgentFailureReason.FINISHED_WITHOUT_REPORT
        )
        return self.terminal_outcome

    def complete_report(self, report: Report) -> AgentTerminalOutcome:
        self.ensure_active()
        self.terminal_outcome = AgentTerminalOutcome.success(report)
        return self.terminal_outcome

    def fail(self, reason: AgentFailureReason) -> AgentTerminalOutcome:
        self.ensure_active()
        self.terminal_outcome = AgentTerminalOutcome.failure(reason)
        return self.terminal_outcome
