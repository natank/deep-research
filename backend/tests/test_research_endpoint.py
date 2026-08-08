from unittest.mock import patch

from fastapi.testclient import TestClient

from app.emailer.schemas import EmailResult
from app.main import app
from app.orchestrator import ResearchResult
from app.searcher.schemas import SourceArticle
from app.writer.schemas import ChartData, ChartDataPoint, Report

client = TestClient(app)


def _result() -> ResearchResult:
    return ResearchResult(
        report=Report(
            topic="topic",
            summary="summary",
            insights=["insight"],
            chart=ChartData(title="chart", points=[ChartDataPoint(label="a", value=1)]),
        ),
        sources=[SourceArticle(title="Title", url="https://a.com", content="content", score=0.5)],
        email=EmailResult(
            status="sent", recipient="demo-user@example.com", report_id="id", filename="id.md"
        ),
    )


def test_research_returns_report_and_email_status() -> None:
    with patch("app.main.run_research", return_value=_result()) as mock_run:
        response = client.post("/research", json={"topic": "solid-state batteries"})

    mock_run.assert_called_once_with("solid-state batteries")
    assert response.status_code == 200
    body = response.json()
    assert body["report"]["topic"] == "topic"
    assert body["sources"][0]["url"] == "https://a.com"
    assert body["email"]["status"] == "sent"


def test_research_rejects_empty_topic() -> None:
    response = client.post("/research", json={"topic": "   "})

    assert response.status_code == 422


def test_research_returns_502_when_pipeline_fails() -> None:
    with patch("app.main.run_research", side_effect=RuntimeError("boom")):
        response = client.post("/research", json={"topic": "topic"})

    assert response.status_code == 502
    assert response.json()["detail"] == "Research failed, please try again"
