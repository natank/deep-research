from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

TOPIC_MAX_LENGTH = 200


class ClarificationAnswer(BaseModel):
    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)

    @field_validator("question_id", "question", "answer")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value


class ResearchContext(BaseModel):
    topic: str = Field(min_length=1, max_length=TOPIC_MAX_LENGTH)
    clarification_answers: list[ClarificationAnswer] = Field(default_factory=list)

    @field_validator("topic")
    @classmethod
    def strip_topic(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("topic must not be empty")
        return value


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
