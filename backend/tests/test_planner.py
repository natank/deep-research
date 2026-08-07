from unittest.mock import MagicMock

import pytest

from app.planner.schemas import SearchPlan, SearchQuery
from app.planner.service import MAX_QUERIES, create_search_plan


def _mock_client(plan: SearchPlan | None) -> MagicMock:
    client = MagicMock()
    client.responses.parse.return_value = MagicMock(output_parsed=plan)
    return client


def test_create_search_plan_returns_parsed_plan() -> None:
    plan = SearchPlan(
        topic="solid-state batteries",
        queries=[
            SearchQuery(query="solid-state battery breakthroughs 2026", rationale="recent news"),
            SearchQuery(query="solid-state battery vs lithium-ion", rationale="background"),
        ],
    )
    client = _mock_client(plan)

    result = create_search_plan("solid-state batteries", client=client)

    assert result == plan
    client.responses.parse.assert_called_once()
    _, kwargs = client.responses.parse.call_args
    assert kwargs["text_format"] is SearchPlan
    assert "solid-state batteries" in kwargs["input"][-1]["content"]


def test_create_search_plan_caps_queries_at_max() -> None:
    queries = [
        SearchQuery(query=f"query {i}", rationale="reason") for i in range(MAX_QUERIES + 5)
    ]
    plan = SearchPlan(topic="topic", queries=queries)
    client = _mock_client(plan)

    result = create_search_plan("topic", client=client)

    assert len(result.queries) == MAX_QUERIES


def test_create_search_plan_raises_when_unparsed() -> None:
    client = _mock_client(None)

    with pytest.raises(ValueError, match="did not return a parseable search plan"):
        create_search_plan("topic", client=client)
