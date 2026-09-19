import pytest
from pydantic import ValidationError

from app.research.schemas import (
    ClarificationAnswer,
    ExecutionLimits,
    OrchestrationMode,
    ResearchContext,
    ResearchRun,
    RunMetrics,
    RunStatus,
)


def test_research_run_defaults_to_code_mode_and_pending_status() -> None:
    run = ResearchRun(context=ResearchContext(topic="topic"))

    assert run.orchestration_mode is OrchestrationMode.CODE
    assert run.status is RunStatus.PENDING
    assert run.limits.max_sources == 8
    assert run.metrics.search_count == 0


def test_research_context_preserves_structured_answers() -> None:
    answer = ClarificationAnswer(
        question_id="timeframe",
        question="Which timeframe should be covered?",
        answer="Since 2020",
    )

    context = ResearchContext(topic="renewable energy", clarification_answers=[answer])

    assert context.clarification_answers == [answer]
    assert context.model_dump()["clarification_answers"][0]["question_id"] == "timeframe"


def test_context_text_is_trimmed_and_blank_values_are_rejected() -> None:
    context = ResearchContext(topic="  topic  ")

    assert context.topic == "topic"

    with pytest.raises(ValidationError):
        ResearchContext(topic="   ")

    with pytest.raises(ValidationError):
        ClarificationAnswer(question_id="id", question="question", answer=" ")


def test_invalid_modes_and_statuses_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ResearchRun(
            context=ResearchContext(topic="topic"),
            orchestration_mode="manual",
        )

    with pytest.raises(ValidationError):
        RunMetrics(completion_status="unknown")


def test_execution_limits_reject_negative_values() -> None:
    with pytest.raises(ValidationError):
        ExecutionLimits(max_tool_calls=-1)

    with pytest.raises(ValidationError):
        RunMetrics(duration_ms=-1)


def test_agent_run_and_optional_metrics_serialize() -> None:
    run = ResearchRun(
        context=ResearchContext(topic="topic"),
        orchestration_mode=OrchestrationMode.AGENT,
        status=RunStatus.COMPLETED,
        metrics=RunMetrics(
            search_count=4,
            source_count=8,
            agent_iteration_count=2,
            duration_ms=1250,
            completion_status=RunStatus.COMPLETED,
            api_call_count=6,
            input_tokens=100,
            output_tokens=250,
        ),
    )

    payload = run.model_dump(mode="json")

    assert payload["orchestration_mode"] == "agent"
    assert payload["status"] == "completed"
    assert payload["metrics"]["duration_ms"] == 1250
    assert payload["metrics"]["output_tokens"] == 250
