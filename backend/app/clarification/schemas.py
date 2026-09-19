from pydantic import BaseModel, Field

QUESTION_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,31}$"
TEXT_MAX_LENGTH = 200


class ClarificationQuestion(BaseModel):
    id: str = Field(pattern=QUESTION_ID_PATTERN)
    question: str = Field(min_length=1, max_length=TEXT_MAX_LENGTH)
    purpose: str = Field(min_length=1, max_length=TEXT_MAX_LENGTH)


class ClarificationDecision(BaseModel):
    needs_clarification: bool
    questions: list[ClarificationQuestion] = Field(default_factory=list)
