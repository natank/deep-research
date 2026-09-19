import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.clarification import ClarificationDecision, ClarificationError, decide_clarification
from app.config import settings
from app.orchestrator import ResearchResult, run_research
from app.research.schemas import ResearchContext

logger = logging.getLogger(__name__)

TOPIC_MAX_LENGTH = 200

app = FastAPI(title="Deep Research API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    topic: str = Field(max_length=TOPIC_MAX_LENGTH)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/clarify")
def clarify(request: ResearchRequest) -> ClarificationDecision:
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=422, detail="Topic must not be empty")

    try:
        context = ResearchContext(topic=topic)
        return decide_clarification(context)
    except ClarificationError:
        logger.error("Clarification failed: ClarificationError")
        raise HTTPException(status_code=502, detail="Clarification failed") from None
    except Exception as err:
        logger.error("Clarification failed: %s", type(err).__name__)
        raise HTTPException(status_code=502, detail="Clarification failed") from None


@app.post("/research")
def research(request: ResearchRequest) -> ResearchResult:
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=422, detail="Topic must not be empty")

    try:
        return run_research(topic)
    except Exception:
        logger.exception("Research pipeline failed for topic: %s", topic)
        raise HTTPException(status_code=502, detail="Research failed, please try again") from None


@app.get("/reports/{report_id}")
def download_report(report_id: str) -> FileResponse:
    try:
        uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Report not found") from None

    report_path = Path(settings.reports_dir) / f"{report_id}.md"
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(report_path, media_type="text/markdown", filename=report_path.name)
