from openai import OpenAI

from app.config import settings
from app.planner.schemas import SearchPlan
from app.research.formatting import format_research_context
from app.research.schemas import ResearchContext

MIN_QUERIES = 3
MAX_QUERIES = 8

SYSTEM_PROMPT = (
    "You are a research planning assistant. Given a topic, produce a focused list of "
    f"{MIN_QUERIES}-{MAX_QUERIES} web search queries that together would surface the most "
    "relevant, credible, and varied sources for a research report on that topic. Each query "
    "should target a distinct angle (e.g. background, recent developments, expert opinion, "
    "data/statistics, counterpoints) rather than being near-duplicates of each other."
)


def create_search_plan(
    context: ResearchContext | str, *, client: OpenAI | None = None
) -> SearchPlan:
    research_context = (
        context if isinstance(context, ResearchContext) else ResearchContext(topic=context)
    )
    openai_client = client or OpenAI(api_key=settings.openai_api_key)

    response = openai_client.responses.parse(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": format_research_context(research_context)},
        ],
        text_format=SearchPlan,
    )

    plan = response.output_parsed
    if plan is None:
        raise ValueError("Planner did not return a parseable search plan")

    plan.queries = plan.queries[:MAX_QUERIES]
    return plan
