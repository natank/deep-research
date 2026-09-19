from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

TOPIC_MAX_LENGTH = 200
QUESTION_MAX_LENGTH = 200
ANSWER_MAX_LENGTH = 500
MAX_CLARIFICATION_ANSWERS = 3
DELIMITER_CLOSER = "</untrusted-"


class ClarificationAnswer(BaseModel):
    question_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,31}$")
    question: str = Field(min_length=1, max_length=QUESTION_MAX_LENGTH)
    answer: str = Field(min_length=1, max_length=ANSWER_MAX_LENGTH)

    @field_validator("question_id", "question", "answer")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        if any(ord(character) < 32 for character in value):
            raise ValueError("value contains control characters")
        if DELIMITER_CLOSER in value.casefold():
            raise ValueError("value contains a reserved delimiter")
        return value


class ResearchContext(BaseModel):
    topic: str = Field(min_length=1, max_length=TOPIC_MAX_LENGTH)
    clarification_answers: list[ClarificationAnswer] = Field(
        default_factory=list, max_length=MAX_CLARIFICATION_ANSWERS
    )

    @field_validator("topic")
    @classmethod
    def strip_topic(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("topic must not be empty")
        if any(ord(character) < 32 for character in value):
            raise ValueError("topic contains control characters")
        if DELIMITER_CLOSER in value.casefold():
            raise ValueError("topic contains a reserved delimiter")
        return value

    @model_validator(mode="after")
    def validate_answer_ids(self) -> "ResearchContext":
        ids = [answer.question_id for answer in self.clarification_answers]
        if len(ids) != len(set(ids)):
            raise ValueError("clarification question ids must be unique")
        return self


class OrchestrationMode(StrEnum):
    CODE = "code"
    AGENT = "agent"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionLimits(BaseModel):
    max_clarification_questions: int = Field(default=3, ge=0)
    max_searches: int = Field(default=8, ge=0)
    max_sources: int = Field(default=8, ge=0)
    max_tool_calls: int = Field(default=12, ge=0)
    max_agent_iterations: int = Field(default=5, ge=0)


class RunMetrics(BaseModel):
    search_count: int = Field(default=0, ge=0)
    source_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    agent_iteration_count: int = Field(default=0, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    completion_status: RunStatus | None = None
    api_call_count: int = Field(default=0, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class ResearchRun(BaseModel):
    context: ResearchContext
    orchestration_mode: OrchestrationMode = OrchestrationMode.CODE
    status: RunStatus = RunStatus.PENDING
    limits: ExecutionLimits = Field(default_factory=ExecutionLimits)
    metrics: RunMetrics = Field(default_factory=RunMetrics)
