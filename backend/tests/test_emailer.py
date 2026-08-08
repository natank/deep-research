from pathlib import Path

from app.emailer.service import SIMULATED_RECIPIENT, send_report
from app.writer.schemas import ChartData, ChartDataPoint, Report


def _report() -> Report:
    return Report(
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


def test_send_report_writes_markdown_file(tmp_path: Path) -> None:
    result = send_report(_report(), reports_dir=tmp_path)

    written = (tmp_path / result.filename).read_text(encoding="utf-8")
    assert "# Research Report: solid-state batteries" in written
    assert "Insight one" in written
    assert "2024: 250" in written


def test_send_report_returns_success_status(tmp_path: Path) -> None:
    result = send_report(_report(), reports_dir=tmp_path)

    assert result.status == "sent"
    assert result.recipient == SIMULATED_RECIPIENT
    assert result.filename == f"{result.report_id}.md"


def test_send_report_creates_reports_dir_if_missing(tmp_path: Path) -> None:
    missing_dir = tmp_path / "nested" / "reports"

    result = send_report(_report(), reports_dir=missing_dir)

    assert (missing_dir / result.filename).exists()


def test_send_report_generates_unique_report_ids(tmp_path: Path) -> None:
    first = send_report(_report(), reports_dir=tmp_path)
    second = send_report(_report(), reports_dir=tmp_path)

    assert first.report_id != second.report_id
