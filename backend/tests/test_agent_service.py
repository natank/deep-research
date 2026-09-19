from unittest.mock import MagicMock

from app.agent.schemas import (
    AgentExecutionState,
    AgentOperation,
    AgentTerminalStatus,
    InspectSourceResult,
    ReportResult,
    RevisedPlanResult,
    SearchResult,
    SourceEnvelope,
)
from app.agent.service import OpenAIAgentModel, execute_agent
from app.research.schemas import ResearchContext, ResearchRun
from app.writer.schemas import ChartData, ChartDataPoint, Report


def _report() -> Report:
    return Report(
        topic="topic",
        summary="summary",
        insights=["insight"],
        chart=ChartData(title="chart", points=[ChartDataPoint(label="a", value=1)]),
    )


def _source() -> SourceEnvelope:
    return SourceEnvelope(
        source_id="src_1",
        title="Title",
        url="https://example.com",
        content="content",
        score=0.5,
    )


class FakeModel:
    def __init__(self, actions: list[dict[str, object]]) -> None:
        self.actions = iter(actions)

    def choose_action(self, state: object) -> dict[str, object]:
        return next(self.actions)


class FakeExecutor:
    def search(self, state: object, query: str) -> SearchResult:
        return SearchResult(operation=AgentOperation.SEARCH, sources=[_source()])

    def revise_plan(self, state: object, queries: list[str]) -> RevisedPlanResult:
        return RevisedPlanResult(operation=AgentOperation.REVISE_PLAN, queries=queries)

    def inspect_source(self, state: object, source_id: str) -> InspectSourceResult:
        return InspectSourceResult(operation=AgentOperation.INSPECT_SOURCE, source=_source())

    def write_report(self, run: ResearchRun, state: object) -> ReportResult:
        return ReportResult(operation=AgentOperation.WRITE_REPORT, report=_report())


def test_agent_loop_adapts_plan_and_writes_report_from_sources() -> None:
    state = execute_agent(
        ResearchRun(context=ResearchContext(topic="topic")),
        model=FakeModel(
            [
                {"operation": "search", "query": "first query"},
                {"operation": "revise_plan", "queries": ["revised query"]},
                {"operation": "search", "query": "second query"},
                {"operation": "write_report"},
            ]
        ),
        executor=FakeExecutor(),
    )

    assert state.terminal_outcome is not None
    assert state.terminal_outcome.status is AgentTerminalStatus.SUCCESS
    assert state.terminal_outcome.report == _report()
    assert state.queries == ["revised query"]
    assert state.source_count == 2


def test_agent_write_report_without_sources_fails_without_provider_calls() -> None:
    executor = MagicMock()
    state = execute_agent(
        ResearchRun(context=ResearchContext(topic="topic")),
        model=FakeModel([{"operation": "write_report"}] * 3),
        executor=executor,
    )

    assert state.terminal_outcome is not None
    assert state.terminal_outcome.status is AgentTerminalStatus.FAILURE
    executor.write_report.assert_not_called()


def test_agent_finish_without_report_is_failure() -> None:
    state = execute_agent(
        ResearchRun(context=ResearchContext(topic="topic")),
        model=FakeModel([{"operation": "finish"}]),
        executor=FakeExecutor(),
    )

    assert state.terminal_outcome is not None
    assert state.terminal_outcome.status is AgentTerminalStatus.FAILURE


def test_openai_adapter_uses_one_strict_action_and_delimited_user_state() -> None:
    client = MagicMock()
    client.responses.parse.return_value.output_parsed = MagicMock(
        model_dump=lambda **_: {"operation": "search", "query": "query"}
    )
    model = OpenAIAgentModel(client=client)
    model.choose_action(
        AgentExecutionState(
            context=ResearchContext(
                topic="topic",
                clarification_answers=[
                    {"question_id": "q1", "question": "Scope?", "answer": "Higher education"}
                ],
            )
        )
    )

    _, kwargs = client.responses.parse.call_args
    assert kwargs["text_format"].__name__ == "AgentDecision"
    assert "Higher education" in kwargs["input"][1]["content"]
    assert "Higher education" not in kwargs["input"][0]["content"]
