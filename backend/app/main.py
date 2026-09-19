import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.agent.exceptions import AgentRunError
from app.clarification import ClarificationDecision, ClarificationError, decide_clarification
from app.config import settings
from app.orchestrator import ResearchResult, run_agent, run_research
from app.research.schemas import (
    MAX_CLARIFICATION_ANSWERS,
    ClarificationAnswer,
    ExecutionLimits,
    OrchestrationMode,
    ResearchContext,
    ResearchRun,
)

logger = logging.getLogger(__name__)

TOPIC_MAX_LENGTH = 200

app = FastAPI(title="Deep Research API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TopicRequest(BaseModel):
    topic: str = Field(max_length=TOPIC_MAX_LENGTH)


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    topic: str = Field(min_length=1, max_length=TOPIC_MAX_LENGTH)
    clarification_answers: list[ClarificationAnswer] = Field(
        default_factory=list, max_length=MAX_CLARIFICATION_ANSWERS
    )
    orchestration_mode: OrchestrationMode = OrchestrationMode.CODE


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/clarify")
def clarify(request: TopicRequest) -> ClarificationDecision:
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
    try:
        context = ResearchContext(
            topic=request.topic,
            clarification_answers=request.clarification_answers,
        )
        run = ResearchRun(
            context=context,
            orchestration_mode=request.orchestration_mode,
            limits=ExecutionLimits(),
        )
        if run.orchestration_mode is OrchestrationMode.AGENT:
            return run_agent(run)
        return run_research(run.context)
    except ValidationError as err:
        raise HTTPException(status_code=422, detail="Invalid research context") from err
    except AgentRunError as err:
        logger.error("Agent pipeline failed: reason=%s", err.reason)
        raise HTTPException(status_code=502, detail="Research failed, please try again") from None
    except Exception as err:
        logger.error("Research pipeline failed: %s", type(err).__name__)
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
