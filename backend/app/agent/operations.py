from app.agent.exceptions import AgentContractError, AgentFailureReason, AgentLimitError
from app.agent.limits import (
    reserve_inspect_source,
    reserve_plan_revision,
    reserve_report_attempt,
    reserve_search,
    reserve_tool_call,
)
from app.agent.schemas import (
    AgentAction,
    AgentExecutionState,
    AgentOperation,
    FinishAction,
    InspectSourceAction,
    RevisePlanAction,
    SearchAction,
    SourceEnvelope,
    WriteReportAction,
)
from app.agent.validation import require_known_source, validate_plan_queries
from app.writer.schemas import Report

MAX_RETRIES_PER_OPERATION = 1


def reserve_action(state: AgentExecutionState, action: AgentAction) -> None:
    """Reserve all applicable counters before the corresponding provider call."""
    state.ensure_active()
    if isinstance(action, SearchAction):
        reserve_search(state)
    elif isinstance(action, InspectSourceAction):
        require_known_source(state, action.source_id)
        reserve_inspect_source(state)
    elif isinstance(action, RevisePlanAction):
        validate_plan_queries(action.queries)
        reserve_plan_revision(state)
    elif isinstance(action, WriteReportAction):
        reserve_report_attempt(state)
    elif isinstance(action, FinishAction):
        state.finish_without_report()
    else:
        raise AgentContractError


def reserve_retry(state: AgentExecutionState, operation: AgentOperation) -> None:
    state.ensure_active()
    retries = state.retry_counts.get(operation, 0)
    if retries >= MAX_RETRIES_PER_OPERATION:
        raise AgentLimitError
    reserve_tool_call(state)
    state.retry_counts[operation] = retries + 1


def add_sources(state: AgentExecutionState, sources: list[SourceEnvelope]) -> None:
    state.ensure_active()
    remaining = state.limits.max_sources - state.source_count
    if len(sources) > remaining:
        raise AgentLimitError
    state.sources.extend(sources)
    state.source_count += len(sources)


def apply_plan_revision(state: AgentExecutionState, action: RevisePlanAction) -> list[str]:
    state.ensure_active()
    queries = validate_plan_queries(action.queries)
    state.queries = queries
    state.revision_count += 1
    return queries


def complete_report(state: AgentExecutionState, report: Report) -> None:
    state.complete_report(report)


def fail_provider_operation(state: AgentExecutionState) -> None:
    state.fail(AgentFailureReason.PROVIDER_FAILURE)


def fail_timeout(state: AgentExecutionState) -> None:
    state.fail(AgentFailureReason.TIMED_OUT)


def fail_cancelled(state: AgentExecutionState) -> None:
    state.fail(AgentFailureReason.CANCELLED)
