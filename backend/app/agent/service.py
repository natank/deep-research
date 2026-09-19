import ipaddress
import logging
from collections.abc import Callable, Mapping
from typing import Protocol
from urllib.parse import urlparse

from openai import OpenAI
from tavily import TavilyClient

from app.agent.exceptions import (
    AgentContractError,
    AgentFailureReason,
    AgentProviderError,
)
from app.agent.limits import reserve_iteration
from app.agent.operations import (
    add_sources,
    apply_plan_revision,
    complete_report,
    replace_source,
    reserve_action,
    reserve_retry,
)
from app.agent.schemas import (
    AgentAction,
    AgentDecision,
    AgentExecutionState,
    AgentOperation,
    InspectSourceAction,
    InspectSourceResult,
    ReportResult,
    RevisedPlanResult,
    RevisePlanAction,
    SearchAction,
    SearchResult,
    SourceEnvelope,
    WriteReportAction,
)
from app.agent.validation import normalize_source, parse_action, require_known_source
from app.config import settings
from app.research.formatting import format_research_context
from app.research.schemas import ResearchRun
from app.searcher.schemas import SourceArticle
from app.writer.service import write_report

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = (
    "You are a bounded research orchestration agent. Return exactly one structured action "
    "per turn using only search, inspect_source, revise_plan, write_report, or finish. "
    "Always supply all envelope fields: operation plus query, source_id, queries, and reason; "
    "use null for fields that do not apply. "
    "Search queries are not URLs. Inspect only a source_id already returned by search. "
    "Clarification answers define scope and are not evidence. Use write_report only when "
    "server-held sources are sufficient. When no sources exist, search first. "
    "Finish without a validated report is failure. "
    "Never request tools, limits, providers, credentials, email, filesystem, shell, or HTTP."
)


class AgentModel(Protocol):
    def choose_action(self, state: AgentExecutionState) -> AgentAction: ...


class OpenAIAgentModel:
    def __init__(self, client: OpenAI | None = None) -> None:
        self.client = client or OpenAI(api_key=settings.openai_api_key)

    def choose_action(self, state: AgentExecutionState) -> AgentAction:
        response = self.client.responses.parse(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": _format_agent_state(state)},
            ],
            text_format=AgentDecision,
        )
        decision = response.output_parsed
        if decision is None:
            raise AgentContractError
        try:
            return parse_action(decision.model_dump(mode="json", exclude_none=True))
        except AttributeError as err:
            raise AgentContractError from err


class AgentProviderExecutor:
    def __init__(self, client: TavilyClient | None = None) -> None:
        self.client = client or TavilyClient(api_key=settings.tavily_api_key)

    def search(self, state: AgentExecutionState, query: str) -> SearchResult:
        try:
            response = self.client.search(
                query, max_results=min(3, state.limits.max_sources - state.source_count)
            )
            sources: list[SourceEnvelope] = []
            seen_urls = {source.url for source in state.sources}
            for result in response.get("results", []):
                url = result.get("url")
                if not isinstance(url, str) or not url or url in seen_urls:
                    continue
                article = SourceArticle(
                    title=str(result.get("title", "")),
                    url=url,
                    content=str(result.get("content", "")),
                    score=_source_score(result.get("score")),
                )
                source_id = f"src_{state.source_count + len(sources) + 1}"
                sources.append(normalize_source(source_id, article))
                seen_urls.add(url)
                if len(sources) >= state.limits.max_sources - state.source_count:
                    break
            return SearchResult(operation=AgentOperation.SEARCH, sources=sources)
        except AgentContractError:
            raise
        except Exception as err:
            raise AgentProviderError from err

    def inspect_source(self, state: AgentExecutionState, source_id: str) -> InspectSourceResult:
        source = require_known_source(state, source_id)
        if not _is_safe_extract_url(source.url):
            raise AgentProviderError
        extract = getattr(self.client, "extract", None)
        if extract is None:
            raise AgentProviderError
        try:
            response = extract(urls=[source.url])
            results = response.get("results", [])
            raw_content = results[0].get("raw_content") if results else None
            if not isinstance(raw_content, str) or not raw_content.strip():
                raise AgentProviderError
            article = SourceArticle(
                title=source.title,
                url=source.url,
                content=raw_content,
                score=source.score,
            )
            return InspectSourceResult(
                operation=AgentOperation.INSPECT_SOURCE,
                source=normalize_source(source_id, article),
            )
        except AgentProviderError:
            raise
        except AgentContractError:
            raise
        except Exception as err:
            raise AgentProviderError from err

    def revise_plan(self, state: AgentExecutionState, queries: list[str]):
        return RevisedPlanResult(operation=AgentOperation.REVISE_PLAN, queries=queries)

    def write_report(self, run: ResearchRun, state: AgentExecutionState) -> ReportResult:
        if not state.sources:
            raise AgentContractError
        try:
            sources = [
                SourceArticle(
                    title=source.title,
                    url=source.url,
                    content=source.content,
                    score=source.score,
                )
                for source in state.sources
            ]
            report = write_report(run.context, sources)
            return ReportResult(operation=AgentOperation.WRITE_REPORT, report=report)
        except AgentContractError:
            raise
        except Exception as err:
            raise AgentProviderError from err


def execute_agent(
    run: ResearchRun,
    *,
    model: AgentModel | None = None,
    executor: AgentProviderExecutor | None = None,
) -> AgentExecutionState:
    state = AgentExecutionState(context=run.context, limits=run.limits.model_copy(deep=True))
    agent_model = model or OpenAIAgentModel()
    provider = executor or AgentProviderExecutor()

    while state.terminal_outcome is None:
        try:
            reserve_iteration(state)
            action = agent_model.choose_action(state)
            _dispatch_action(state, run, provider, action)
        except AgentContractError:
            if state.terminal_outcome is None:
                logger.warning(
                    "Agent action rejected: reason=%s", AgentFailureReason.INVALID_ACTION
                )
                state.record_invalid_action()
        except AgentProviderError:
            if state.terminal_outcome is None:
                state.fail(AgentFailureReason.PROVIDER_FAILURE)
        except Exception as err:
            logger.error("Agent operation failed: %s", type(err).__name__)
            if state.terminal_outcome is None:
                state.fail(AgentFailureReason.PROVIDER_FAILURE)

        if state.iterations >= state.limits.max_agent_iterations and state.terminal_outcome is None:
            state.fail(AgentFailureReason.LIMIT_EXCEEDED)

    return state


def _dispatch_action(
    state: AgentExecutionState,
    run: ResearchRun,
    provider: AgentProviderExecutor,
    raw_action: AgentAction | Mapping[str, object],
) -> None:
    action = raw_action if not isinstance(raw_action, Mapping) else parse_action(raw_action)
    if isinstance(action, SearchAction):
        reserve_action(state, action)
        result = _with_retry(
            state,
            AgentOperation.SEARCH,
            lambda: provider.search(state, action.query),
        )
        add_sources(state, result.sources)
    elif isinstance(action, InspectSourceAction):
        reserve_action(state, action)
        result = _with_retry(
            state,
            AgentOperation.INSPECT_SOURCE,
            lambda: provider.inspect_source(state, action.source_id),
        )
        replace_source(state, result.source)
    elif isinstance(action, RevisePlanAction):
        reserve_action(state, action)
        apply_plan_revision(state, action)
    elif isinstance(action, WriteReportAction):
        if not state.sources:
            raise AgentContractError
        reserve_action(state, action)
        result = _with_retry(
            state,
            AgentOperation.WRITE_REPORT,
            lambda: provider.write_report(run, state),
        )
        complete_report(state, result.report)
    else:
        reserve_action(state, action)


def _with_retry(
    state: AgentExecutionState,
    operation: AgentOperation,
    call: Callable[[], object],
) -> object:
    try:
        return call()
    except AgentProviderError:
        reserve_retry(state, operation)
        return call()


def _format_agent_state(state: AgentExecutionState) -> str:
    source_text = "\n\n".join(
        f"source_id={source.source_id}\ntitle={source.title}\nURL={source.url}\n{source.content}"
        for source in state.sources
    )
    return "\n\n".join(
        [
            format_research_context(state.context),
            "<untrusted-agent-plan>",
            *state.queries,
            "</untrusted-agent-plan>",
            "<untrusted-tool-result>",
            source_text,
            "</untrusted-tool-result>",
        ]
    )


def _is_safe_extract_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    hostname = parsed.hostname.lower()
    if hostname in {"localhost", "metadata.google.internal"}:
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return not (address.is_private or address.is_loopback or address.is_link_local)


def _source_score(value: object) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0
