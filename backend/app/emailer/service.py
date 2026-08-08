import logging
import uuid
from pathlib import Path

from app.config import settings
from app.emailer.schemas import EmailResult
from app.writer.schemas import Report

logger = logging.getLogger(__name__)

SIMULATED_RECIPIENT = "demo-user@example.com"


def _render_markdown(report: Report) -> str:
    lines = [
        f"# Research Report: {report.topic}",
        "",
        "## Summary",
        report.summary,
        "",
        "## Key Insights",
        *[f"- {insight}" for insight in report.insights],
        "",
        f"## Chart: {report.chart.title}",
        *[f"- {point.label}: {point.value}" for point in report.chart.points],
    ]
    return "\n".join(lines) + "\n"


def send_report(report: Report, *, reports_dir: Path | None = None) -> EmailResult:
    output_dir = reports_dir or Path(settings.reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report_id = str(uuid.uuid4())
    filename = f"{report_id}.md"
    (output_dir / filename).write_text(_render_markdown(report), encoding="utf-8")

    logger.info("Simulated email sent to %s with report %s", SIMULATED_RECIPIENT, report_id)

    return EmailResult(
        status="sent",
        recipient=SIMULATED_RECIPIENT,
        report_id=report_id,
        filename=filename,
    )
