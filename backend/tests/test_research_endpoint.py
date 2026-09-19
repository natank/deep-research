from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agent.exceptions import AgentFailureReason, AgentRunError
from app.clarification.exceptions import ClarificationError
from app.clarification.schemas import ClarificationDecision, ClarificationQuestion
from app.emailer.schemas import EmailResult
from app.main import TOPIC_MAX_LENGTH, app
from app.orchestrator import ResearchResult
from app.research.schemas import ClarificationAnswer, ResearchContext
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

    mock_run.assert_called_once_with(
        ResearchContext(topic="solid-state batteries", clarification_answers=[])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["report"]["topic"] == "topic"
    assert body["sources"][0]["url"] == "https://a.com"
    assert body["email"]["status"] == "sent"


def test_research_passes_clarification_context_to_pipeline() -> None:
    answer = {
        "question_id": "q1",
        "question": "Which timeframe?",
        "answer": "Since 2020",
    }
    with patch("app.main.run_research", return_value=_result()) as mock_run:
        response = client.post(
            "/research",
            json={"topic": "topic", "clarification_answers": [answer]},
        )

    mock_run.assert_called_once_with(
        ResearchContext(
            topic="topic",
            clarification_answers=[ClarificationAnswer(**answer)],
        )
    )
    assert response.status_code == 200


def test_research_agent_mode_runs_agent_without_code_pipeline() -> None:
    with (
        patch("app.main.run_agent", return_value=_result()) as mock_agent,
        patch("app.main.run_research") as mock_code,
    ):
        response = client.post(
            "/research",
            json={"topic": "topic", "orchestration_mode": "agent"},
        )

    assert response.status_code == 200
    mock_agent.assert_called_once()
    mock_code.assert_not_called()


def test_research_agent_failure_is_generic_and_does_not_fallback() -> None:
    with (
        patch("app.main.run_agent", side_effect=AgentRunError(AgentFailureReason.PROVIDER_FAILURE)),
        patch("app.main.run_research") as mock_code,
    ):
        response = client.post(
            "/research",
            json={
                "topic": "sensitive topic",
                "orchestration_mode": "agent",
                "clarification_answers": [
                    {"question_id": "q1", "question": "Which?", "answer": "private answer"}
                ],
            },
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "Research failed, please try again"}
    assert "sensitive topic" not in response.text
    assert "private answer" not in response.text
    mock_code.assert_not_called()


def test_research_rejects_unknown_orchestration_mode() -> None:
    with patch("app.main.run_research") as mock_run:
        response = client.post(
            "/research",
            json={"topic": "topic", "orchestration_mode": "compare"},
        )

    assert response.status_code == 422
    mock_run.assert_not_called()


def test_research_ignores_client_execution_controls() -> None:
    with patch("app.main.run_research", return_value=_result()) as mock_run:
        response = client.post(
            "/research",
            json={
                "topic": "topic",
                "orchestration_mode": "code",
                "limits": {"max_tool_calls": 0},
                "tools": ["untrusted-tool"],
                "model": "client-model",
                "api_key": "client-secret",
            },
        )

    assert response.status_code == 200
    mock_run.assert_called_once_with(ResearchContext(topic="topic", clarification_answers=[]))


def test_research_rejects_invalid_clarification_context_before_pipeline() -> None:
    with patch("app.main.run_research") as mock_run:
        response = client.post(
            "/research",
            json={
                "topic": "topic",
                "clarification_answers": [
                    {"question_id": "q1", "question": "Which?", "answer": "one"},
                    {"question_id": "q1", "question": "Duplicate?", "answer": "two"},
                ],
            },
        )

    assert response.status_code == 422
    mock_run.assert_not_called()


def test_research_rejects_empty_topic() -> None:
    response = client.post("/research", json={"topic": "   "})

    assert response.status_code == 422


def test_research_rejects_topic_over_max_length() -> None:
    response = client.post("/research", json={"topic": "a" * (TOPIC_MAX_LENGTH + 1)})

    assert response.status_code == 422


def test_research_accepts_topic_at_max_length() -> None:
    with patch("app.main.run_research", return_value=_result()):
        response = client.post("/research", json={"topic": "a" * TOPIC_MAX_LENGTH})

    assert response.status_code == 200


def test_research_returns_502_when_pipeline_fails() -> None:
    with patch("app.main.run_research", side_effect=RuntimeError("topic and answer")):
        response = client.post(
            "/research",
            json={
                "topic": "topic",
                "clarification_answers": [
                    {"question_id": "q1", "question": "Which?", "answer": "answer"}
                ],
            },
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "Research failed, please try again"
    assert "topic" not in response.text
    assert "answer" not in response.text


def test_clarify_returns_decision_for_topic_only_request() -> None:
    decision = ClarificationDecision(
        needs_clarification=True,
        questions=[
            ClarificationQuestion(
                id="q1", question="Which timeframe?", purpose="A timeframe narrows the research."
            )
        ],
    )
    with patch("app.main.decide_clarification", return_value=decision) as mock_decide:
        response = client.post(
            "/clarify",
            json={"topic": "artificial intelligence in education", "limits": {"max_sources": 0}},
        )

    mock_decide.assert_called_once()
    assert response.status_code == 200
    assert response.json() == decision.model_dump(mode="json")


def test_clarify_rejects_empty_topic() -> None:
    response = client.post("/clarify", json={"topic": "   "})

    assert response.status_code == 422


def test_clarify_maps_clarification_failure_to_generic_502() -> None:
    with patch("app.main.decide_clarification", side_effect=ClarificationError):
        response = client.post("/clarify", json={"topic": "topic"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Clarification failed"}


def test_clarify_maps_unexpected_failure_to_generic_502() -> None:
    with patch("app.main.decide_clarification", side_effect=RuntimeError("provider details")):
        response = client.post("/clarify", json={"topic": "topic"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Clarification failed"}
