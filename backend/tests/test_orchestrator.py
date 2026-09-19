from unittest.mock import patch

from app.emailer.schemas import EmailResult
from app.orchestrator import run_research
from app.planner.schemas import SearchPlan, SearchQuery
from app.research.schemas import ResearchContext
from app.searcher.schemas import SourceArticle
from app.writer.schemas import ChartData, ChartDataPoint, Report


def _plan() -> SearchPlan:
    return SearchPlan(topic="topic", queries=[SearchQuery(query="q1", rationale="r")])


def _sources() -> list[SourceArticle]:
    return [SourceArticle(title="Title", url="https://a.com", content="content", score=0.5)]


def _report() -> Report:
    return Report(
        topic="topic",
        summary="summary",
        insights=["insight"],
        chart=ChartData(title="chart", points=[ChartDataPoint(label="a", value=1)]),
    )


def _email() -> EmailResult:
    return EmailResult(
        status="sent", recipient="demo-user@example.com", report_id="id", filename="id.md"
    )


def test_run_research_wires_components_in_order() -> None:
    plan, sources, report, email = _plan(), _sources(), _report(), _email()

    with (
        patch("app.orchestrator.create_search_plan", return_value=plan) as mock_plan,
        patch("app.orchestrator.search_plan", return_value=sources) as mock_search,
        patch("app.orchestrator.write_report", return_value=report) as mock_write,
        patch("app.orchestrator.send_report", return_value=email) as mock_send,
    ):
        result = run_research("topic")

    context = ResearchContext(topic="topic")
    mock_plan.assert_called_once_with(context)
    mock_search.assert_called_once_with(plan)
    mock_write.assert_called_once_with(context, sources)
    mock_send.assert_called_once_with(report)
    assert result.report == report
    assert result.sources == sources
    assert result.email == email
