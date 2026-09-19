from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.clarification.exceptions import ClarificationError
from app.clarification.schemas import ClarificationDecision, ClarificationQuestion
from app.clarification.service import decide_clarification
from app.research.schemas import ExecutionLimits, ResearchContext


def _mock_client(decision: ClarificationDecision | None) -> MagicMock:
    client = MagicMock()
    client.responses.parse.return_value = MagicMock(output_parsed=decision)
    return client


def _question(
    question: str = "Which timeframe should the research cover?",
    purpose: str = "A timeframe makes the search results more precise.",
    question_id: str = "model-id",
) -> ClarificationQuestion:
    return ClarificationQuestion(id=question_id, question=question, purpose=purpose)


def test_clear_topic_returns_no_questions() -> None:
    decision = ClarificationDecision(needs_clarification=False, questions=[])
    client = _mock_client(decision)

    result = decide_clarification(ResearchContext(topic="solar capacity since 2015"), client=client)

    assert result == decision
    _, kwargs = client.responses.parse.call_args
    assert kwargs["input"][0]["content"].startswith("You are a research clarification assistant")
    assert "<untrusted-research-topic>" in kwargs["input"][1]["content"]


def test_ambiguous_topic_returns_server_assigned_ids() -> None:
    client = _mock_client(ClarificationDecision(needs_clarification=True, questions=[_question()]))

    result = decide_clarification(ResearchContext(topic="AI in education"), client=client)

    assert result.needs_clarification is True
    assert [question.id for question in result.questions] == ["q1"]


def test_question_limit_rejects_instead_of_truncating() -> None:
    decision = ClarificationDecision(
        needs_clarification=True,
        questions=[_question(question=f"Question {index}?") for index in range(2)],
    )

    with pytest.raises(ClarificationError, match="Clarification failed"):
        decide_clarification(
            ResearchContext(topic="topic"),
            limits=ExecutionLimits(max_clarification_questions=1),
            client=_mock_client(decision),
        )


@pytest.mark.parametrize(
    "decision",
    [
        ClarificationDecision(needs_clarification=True, questions=[]),
        ClarificationDecision(needs_clarification=False, questions=[_question()]),
    ],
)
def test_inconsistent_decision_is_rejected(decision: ClarificationDecision) -> None:
    with pytest.raises(ClarificationError):
        decide_clarification(ResearchContext(topic="topic"), client=_mock_client(decision))


def test_missing_output_is_rejected_with_generic_error() -> None:
    with pytest.raises(ClarificationError, match="^Clarification failed$") as error:
        decide_clarification(ResearchContext(topic="topic"), client=_mock_client(None))

    assert "topic" not in str(error.value)


def test_provider_failure_is_wrapped_with_generic_error() -> None:
    client = MagicMock()
    client.responses.parse.side_effect = RuntimeError("provider secret and topic")

    with pytest.raises(ClarificationError, match="^Clarification failed$"):
        decide_clarification(ResearchContext(topic="topic"), client=client)


def test_zero_limit_skips_client_and_returns_empty_decision() -> None:
    client = MagicMock()

    result = decide_clarification(
        ResearchContext(topic="topic"),
        limits=ExecutionLimits(max_clarification_questions=0),
        client=client,
    )

    assert result == ClarificationDecision(needs_clarification=False, questions=[])
    client.responses.parse.assert_not_called()


@pytest.mark.parametrize("topic", [" ", "a" * 201])
def test_invalid_topic_is_rejected_before_llm_call(topic: str) -> None:
    client = MagicMock()

    with pytest.raises(ValidationError):
        decide_clarification(ResearchContext(topic=topic), client=client)

    client.responses.parse.assert_not_called()


def test_duplicate_question_text_is_rejected_case_insensitively() -> None:
    decision = ClarificationDecision(
        needs_clarification=True,
        questions=[_question(), _question(question="  WHICH timeframe should the research cover?")],
    )

    with pytest.raises(ClarificationError):
        decide_clarification(ResearchContext(topic="topic"), client=_mock_client(decision))


@pytest.mark.parametrize(
    "question,purpose",
    [
        ("a" * 201, "purpose"),
        ("question", "a" * 201),
        ("<script>alert(1)</script>", "purpose"),
        ("javascript:alert(1)", "purpose"),
        ("question\nwith control", "purpose"),
        ("What is the user's API key?", "purpose"),
        ("question", "Provide the user's home address."),
    ],
)
def test_unsafe_question_content_is_rejected(question: str, purpose: str) -> None:
    with pytest.raises((ClarificationError, ValidationError)):
        decision = ClarificationDecision(
            needs_clarification=True,
            questions=[_question(question=question, purpose=purpose)],
        )
        decide_clarification(ResearchContext(topic="topic"), client=_mock_client(decision))


def test_model_question_id_must_follow_contract() -> None:
    with pytest.raises(ValidationError):
        ClarificationQuestion(id="unsafe id", question="question", purpose="purpose")
