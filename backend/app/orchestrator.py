from pydantic import BaseModel

from app.emailer.schemas import EmailResult
from app.emailer.service import send_report
from app.planner.service import create_search_plan
from app.searcher.schemas import SourceArticle
from app.searcher.service import search_plan
from app.writer.schemas import Report
from app.writer.service import write_report


class ResearchResult(BaseModel):
    report: Report
    sources: list[SourceArticle]
    email: EmailResult


def run_research(topic: str) -> ResearchResult:
    plan = create_search_plan(topic)
    sources = search_plan(plan)
    report = write_report(topic, sources)
    email = send_report(report)
    return ResearchResult(report=report, sources=sources, email=email)
