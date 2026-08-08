from unittest.mock import MagicMock

import pytest

from app.searcher.schemas import SourceArticle
from app.writer.schemas import ChartData, ChartDataPoint, Report
from app.writer.service import write_report


def _mock_client(report: Report | None) -> MagicMock:
    client = MagicMock()
    client.responses.parse.return_value = MagicMock(output_parsed=report)
    return client


def _source(url: str = "https://a.com") -> SourceArticle:
    return SourceArticle(title="Title", url=url, content="Some content", score=0.5)


def test_write_report_returns_parsed_report() -> None:
    report = Report(
        topic="solid-state batteries",
        summary="A summary of the findings.",
        insights=["Insight one", "Insight two"],
        chart=ChartData(
            title="Energy density by year",
            points=[
                ChartDataPoint(label="2024", value=250),
                ChartDataPoint(label="2026", value=400),
            ],
        ),
    )
    client = _mock_client(report)
    sources = [_source("https://a.com"), _source("https://b.com")]

    result = write_report("solid-state batteries", sources, client=client)

    assert result == report
    client.responses.parse.assert_called_once()
    _, kwargs = client.responses.parse.call_args
    assert kwargs["text_format"] is Report
    user_content = kwargs["input"][-1]["content"]
    assert "solid-state batteries" in user_content
    assert "https://a.com" in user_content
    assert "https://b.com" in user_content


def test_write_report_raises_when_unparsed() -> None:
    client = _mock_client(None)

    with pytest.raises(ValueError, match="did not return a parseable report"):
        write_report("topic", [_source()], client=client)
