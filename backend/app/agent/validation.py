from collections.abc import Mapping
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.agent.exceptions import AgentContractError
from app.agent.limits import MAX_QUERY_LENGTH, MAX_STORED_QUERIES
from app.agent.schemas import AgentAction, AgentExecutionState, SourceEnvelope
from app.searcher.schemas import SourceArticle

_ACTION_ADAPTER = TypeAdapter(AgentAction)
DELIMITER_CLOSER = "</untrusted-"


def _safe_text(value: str, *, max_length: int = MAX_QUERY_LENGTH) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > max_length:
        raise AgentContractError
    if any(ord(character) < 32 for character in normalized):
        raise AgentContractError
    if DELIMITER_CLOSER in normalized.casefold():
        raise AgentContractError
    return normalized


def parse_action(value: Mapping[str, Any]) -> AgentAction:
    try:
        action = _ACTION_ADAPTER.validate_python(value)
    except ValidationError as err:
        raise AgentContractError from err

    if hasattr(action, "query"):
        action.query = _safe_text(action.query)
    if hasattr(action, "queries"):
        action.queries = [_safe_text(query) for query in action.queries]
    return action


def validate_plan_queries(queries: list[str]) -> list[str]:
    if not 1 <= len(queries) <= MAX_STORED_QUERIES:
        raise AgentContractError
    return [_safe_text(query) for query in queries]


def normalize_source(source_id: str, article: SourceArticle) -> SourceEnvelope:
    try:
        envelope = SourceEnvelope.from_article(
            source_id,
            SourceArticle(
                title=_normalize_provider_text(article.title),
                url=article.url,
                content=_normalize_provider_text(article.content),
                score=article.score,
            ),
        )
    except ValidationError as err:
        raise AgentContractError from err
    for value in (envelope.url,):
        if any(ord(character) < 32 for character in value):
            raise AgentContractError
        if DELIMITER_CLOSER in value.casefold():
            raise AgentContractError
    return envelope


def require_known_source(state: AgentExecutionState, source_id: str) -> SourceEnvelope:
    for source in state.sources:
        if source.source_id == source_id:
            return source
    raise AgentContractError


def _normalize_provider_text(value: str) -> str:
    value = "".join(" " if ord(character) < 32 else character for character in value)
    return value.replace(DELIMITER_CLOSER, "< /untrusted-")
