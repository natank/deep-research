from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    query: str = Field(description="A concrete, executable web search query.")
    rationale: str = Field(description="Why this query helps research the topic.")


class SearchPlan(BaseModel):
    topic: str
    queries: list[SearchQuery]
