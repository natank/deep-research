from unittest.mock import MagicMock

from app.planner.schemas import SearchPlan, SearchQuery
from app.searcher.service import MAX_SOURCES, search_plan


def _mock_client(responses: list[dict]) -> MagicMock:
    client = MagicMock()
    client.search.side_effect = responses
    return client


def _result(url: str, title: str = "Title", score: float = 0.5) -> dict:
    return {"url": url, "title": title, "content": "Some content", "score": score}


def test_search_plan_normalizes_and_ranks_by_score() -> None:
    plan = SearchPlan(topic="topic", queries=[SearchQuery(query="q1", rationale="r")])
    client = _mock_client(
        [{"results": [_result("https://a.com", score=0.2), _result("https://b.com", score=0.9)]}]
    )

    sources = search_plan(plan, client=client)

    assert [s.url for s in sources] == ["https://b.com", "https://a.com"]


def test_search_plan_dedupes_by_url_across_queries() -> None:
    plan = SearchPlan(
        topic="topic",
        queries=[SearchQuery(query="q1", rationale="r"), SearchQuery(query="q2", rationale="r")],
    )
    client = _mock_client(
        [
            {"results": [_result("https://a.com", score=0.5)]},
            {"results": [_result("https://a.com", score=0.9)]},
        ]
    )

    sources = search_plan(plan, client=client)

    assert len(sources) == 1
    assert sources[0].score == 0.5


def test_search_plan_caps_at_max_sources() -> None:
    plan = SearchPlan(topic="topic", queries=[SearchQuery(query="q1", rationale="r")])
    results = [
        _result(f"https://site{i}.com", score=1.0 - i * 0.01) for i in range(MAX_SOURCES + 5)
    ]
    client = _mock_client([{"results": results}])

    sources = search_plan(plan, client=client)

    assert len(sources) == MAX_SOURCES


def test_search_plan_skips_results_without_url() -> None:
    plan = SearchPlan(topic="topic", queries=[SearchQuery(query="q1", rationale="r")])
    client = _mock_client([{"results": [{"title": "No URL", "content": "x", "score": 0.5}]}])

    sources = search_plan(plan, client=client)

    assert sources == []
