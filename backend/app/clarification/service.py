import re

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from app.clarification.exceptions import ClarificationError
from app.clarification.schemas import ClarificationDecision
from app.config import settings
from app.research.schemas import ExecutionLimits, ResearchContext

SYSTEM_PROMPT = (
    "You are a research clarification assistant. Decide whether the research topic "
    "is specific enough to search effectively. Ask only focused, answerable questions "
    "that materially improve the research scope. Do not ask for secrets, credentials, "
    "API keys, passwords, tokens, government identifiers, home addresses, or other "
    "sensitive personal information. Avoid duplicate questions. Return no questions "
    "when the topic is sufficiently clear."
)

_HTML_PATTERN = re.compile(r"<[^>]*>")
_SECRET_PATTERN = re.compile(
    r"\b(?:api[\s_-]*key|access[\s_-]*token|auth(?:entication)?[\s_-]*token|"
    r"password|passphrase|secret|private[\s_-]*key|seed[\s_-]*phrase|"
    r"social[\s_-]*security|ssn|government[\s_-]*(?:id|identification)|"
    r"driver['’]?s[\s_-]*license|home[\s_-]*address|credit[\s_-]*card)\b",
    re.IGNORECASE,
)
_JAVASCRIPT_PATTERN = re.compile(r"\bjavascript\s*:", re.IGNORECASE)


def decide_clarification(
    context: ResearchContext,
    *,
    limits: ExecutionLimits | None = None,
    client: OpenAI | None = None,
) -> ClarificationDecision:
    execution_limits = limits or ExecutionLimits()
    max_questions = execution_limits.max_clarification_questions
    if max_questions == 0:
        return ClarificationDecision(needs_clarification=False, questions=[])

    openai_client = client or OpenAI(api_key=settings.openai_api_key)
    try:
        response = openai_client.responses.parse(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Maximum questions: {max_questions}\n"
                        "<untrusted-research-topic>\n"
                        f"{context.topic}\n"
                        "</untrusted-research-topic>"
                    ),
                },
            ],
            text_format=ClarificationDecision,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ClarificationError
        decision = ClarificationDecision.model_validate(parsed)
        _validate_decision(decision, max_questions)
        return _assign_question_ids(decision)
    except ClarificationError:
        raise
    except (OpenAIError, RuntimeError, ValidationError, AttributeError, TypeError) as err:
        raise ClarificationError from err


def _assign_question_ids(decision: ClarificationDecision) -> ClarificationDecision:
    questions = [
        question.model_copy(update={"id": f"q{index}"})
        for index, question in enumerate(decision.questions, start=1)
    ]
    return decision.model_copy(update={"questions": questions})


def _validate_decision(decision: ClarificationDecision, max_questions: int) -> None:
    if len(decision.questions) > max_questions:
        raise ClarificationError
    if decision.needs_clarification != bool(decision.questions):
        raise ClarificationError

    normalized_questions: set[str] = set()
    for question in decision.questions:
        _validate_plain_text(question.question)
        _validate_plain_text(question.purpose)
        if _SECRET_PATTERN.search(f"{question.question} {question.purpose}"):
            raise ClarificationError
        normalized = " ".join(question.question.split()).casefold()
        if normalized in normalized_questions:
            raise ClarificationError
        normalized_questions.add(normalized)


def _validate_plain_text(value: str) -> None:
    if _HTML_PATTERN.search(value) or _JAVASCRIPT_PATTERN.search(value):
        raise ClarificationError
    if any(ord(character) < 32 for character in value):
        raise ClarificationError
