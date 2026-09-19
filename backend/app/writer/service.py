from openai import OpenAI

from app.config import settings
from app.research.formatting import format_research_context
from app.research.schemas import ResearchContext
from app.searcher.schemas import SourceArticle
from app.writer.schemas import Report

SYSTEM_PROMPT = (
    "You are a research report writer. Given a research topic, optional clarification answers, "
    "and a set of source articles, produce a "
    "report with: a narrative summary synthesizing the sources, a list of key insights, and "
    "chart data that visualizes one quantitative or comparative aspect of the research "
    "(e.g. a trend over time, a comparison across categories) grounded in the sources. Base "
    "every claim only on the provided sources. Clarification answers constrain scope but are "
    "not sources."
)


def _format_sources(sources: list[SourceArticle]) -> str:
    return "\n\n".join(
        f"[{i + 1}] {source.title}\nURL: {source.url}\n{source.content}"
        for i, source in enumerate(sources)
    )


def write_report(
    context: ResearchContext | str, sources: list[SourceArticle], *, client: OpenAI | None = None
) -> Report:
    research_context = (
        context if isinstance(context, ResearchContext) else ResearchContext(topic=context)
    )
    openai_client = client or OpenAI(api_key=settings.openai_api_key)

    response = openai_client.responses.parse(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"{format_research_context(research_context)}\n\n"
                    f"<research-sources>\n{_format_sources(sources)}\n</research-sources>"
                ),
            },
        ],
        text_format=Report,
    )

    report = response.output_parsed
    if report is None:
        raise ValueError("Writer did not return a parseable report")

    return report
