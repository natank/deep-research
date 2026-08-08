from tavily import TavilyClient

from app.config import settings
from app.planner.schemas import SearchPlan
from app.searcher.schemas import SourceArticle

MAX_SOURCES = 8
RESULTS_PER_QUERY = 3


def search_plan(plan: SearchPlan, *, client: TavilyClient | None = None) -> list[SourceArticle]:
    tavily_client = client or TavilyClient(api_key=settings.tavily_api_key)

    sources_by_url: dict[str, SourceArticle] = {}
    for search_query in plan.queries:
        response = tavily_client.search(search_query.query, max_results=RESULTS_PER_QUERY)
        for result in response.get("results", []):
            url = result.get("url")
            if not url or url in sources_by_url:
                continue
            sources_by_url[url] = SourceArticle(
                title=result.get("title", ""),
                url=url,
                content=result.get("content", ""),
                score=result.get("score", 0.0),
            )

    ranked = sorted(sources_by_url.values(), key=lambda source: source.score, reverse=True)
    return ranked[:MAX_SOURCES]
