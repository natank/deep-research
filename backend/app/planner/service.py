from openai import OpenAI

from app.config import settings
from app.planner.schemas import SearchPlan

MIN_QUERIES = 3
MAX_QUERIES = 8

SYSTEM_PROMPT = (
    "You are a research planning assistant. Given a topic, produce a focused list of "
    f"{MIN_QUERIES}-{MAX_QUERIES} web search queries that together would surface the most "
    "relevant, credible, and varied sources for a research report on that topic. Each query "
    "should target a distinct angle (e.g. background, recent developments, expert opinion, "
    "data/statistics, counterpoints) rather than being near-duplicates of each other."
)


def create_search_plan(topic: str, *, client: OpenAI | None = None) -> SearchPlan:
    openai_client = client or OpenAI(api_key=settings.openai_api_key)

    response = openai_client.responses.parse(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Topic: {topic}"},
        ],
        text_format=SearchPlan,
    )

    plan = response.output_parsed
    if plan is None:
        raise ValueError("Planner did not return a parseable search plan")

    plan.queries = plan.queries[:MAX_QUERIES]
    return plan
