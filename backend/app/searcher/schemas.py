from pydantic import BaseModel


class SourceArticle(BaseModel):
    title: str
    url: str
    content: str
    score: float
