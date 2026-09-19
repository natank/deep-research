from typing import Protocol

from app.agent.schemas import (
    AgentExecutionState,
    InspectSourceResult,
    ReportResult,
    RevisedPlanResult,
    SearchResult,
)
from app.research.schemas import ResearchRun


class AgentToolExecutor(Protocol):
    """Provider-facing boundary for the PI-08 Agent loop."""

    def search(self, state: AgentExecutionState, query: str) -> SearchResult: ...

    def inspect_source(self, state: AgentExecutionState, source_id: str) -> InspectSourceResult: ...

    def revise_plan(self, state: AgentExecutionState, queries: list[str]) -> RevisedPlanResult: ...

    def write_report(self, run: ResearchRun, state: AgentExecutionState) -> ReportResult: ...
