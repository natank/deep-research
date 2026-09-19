from pydantic import BaseModel

from app.agent.exceptions import AgentFailureReason, AgentRunError
from app.agent.service import execute_agent
from app.emailer.schemas import EmailResult
from app.emailer.service import send_report
from app.planner.service import create_search_plan
from app.research.schemas import ResearchContext, ResearchRun
from app.searcher.schemas import SourceArticle
from app.searcher.service import search_plan
from app.writer.schemas import Report
from app.writer.service import write_report


class ResearchResult(BaseModel):
    report: Report
    sources: list[SourceArticle]
    email: EmailResult


def run_research(context: ResearchContext | str) -> ResearchResult:
    research_context = (
        context if isinstance(context, ResearchContext) else ResearchContext(topic=context)
    )
    plan = create_search_plan(research_context)
    sources = search_plan(plan)
    report = write_report(research_context, sources)
    email = send_report(report)
    return ResearchResult(report=report, sources=sources, email=email)


def run_agent(run: ResearchRun) -> ResearchResult:
    state = execute_agent(run)
    outcome = state.terminal_outcome
    if outcome is None or outcome.report is None:
        reason = outcome.reason if outcome is not None else AgentFailureReason.PROVIDER_FAILURE
        raise AgentRunError(reason)

    sources = [
        SourceArticle(
            title=source.title,
            url=source.url,
            content=source.content,
            score=source.score,
        )
        for source in state.sources
    ]
    email = send_report(outcome.report)
    return ResearchResult(report=outcome.report, sources=sources, email=email)
