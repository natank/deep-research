from typing import TYPE_CHECKING

from app.agent.exceptions import AgentLimitError
from app.research.schemas import ExecutionLimits

if TYPE_CHECKING:
    from app.agent.schemas import AgentExecutionState

MAX_REPORT_ATTEMPTS = 2
MAX_INVALID_ACTIONS = 3
MAX_STORED_QUERIES = 8
MAX_QUERY_LENGTH = 200


def reserve_tool_call(state: "AgentExecutionState") -> None:
    if state.tool_calls >= state.limits.max_tool_calls:
        raise AgentLimitError
    state.tool_calls += 1


def reserve_iteration(state: "AgentExecutionState") -> None:
    if state.iterations >= state.limits.max_agent_iterations:
        raise AgentLimitError
    state.iterations += 1


def reserve_search(state: "AgentExecutionState") -> None:
    if state.searches >= state.limits.max_searches:
        raise AgentLimitError
    if state.source_count >= state.limits.max_sources:
        raise AgentLimitError
    reserve_tool_call(state)
    state.searches += 1


def reserve_inspect_source(state: "AgentExecutionState") -> None:
    reserve_tool_call(state)


def reserve_plan_revision(state: "AgentExecutionState") -> None:
    reserve_tool_call(state)


def reserve_report_attempt(state: "AgentExecutionState") -> None:
    if state.report_attempts >= MAX_REPORT_ATTEMPTS:
        raise AgentLimitError
    reserve_tool_call(state)
    state.report_attempts += 1


def default_limits() -> ExecutionLimits:
    return ExecutionLimits()
