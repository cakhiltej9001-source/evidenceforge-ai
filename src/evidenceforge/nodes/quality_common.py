"""Bounded fixture callback errors and sanitized per-version events."""

from evidenceforge.graph.state import ResearchState
from evidenceforge.identity import stable_id
from evidenceforge.nodes.common import Update, checked_patch, record_data
from evidenceforge.schemas import RunEvent, ToolError


def quality_event(state: ResearchState, role: str, message: str) -> Update:
    identifier = stable_id(
        "quality_event",
        state["run_id"],
        role,
        state["iteration_count"],
        state["revision_count"],
    )
    event = RunEvent(id=identifier, kind=role, message=message)
    return {"events": {identifier: state["events"].get(identifier) or record_data(event)}}


def quality_error(state: ResearchState, role: str, category: str, attempts: int) -> Update:
    identifier = stable_id(
        "quality_error",
        state["run_id"],
        role,
        state["iteration_count"],
        state["revision_count"],
    )
    error = ToolError(
        id=identifier,
        provider=role,
        category=category,
        attempt=1,
        retryable=False,
        message="Structured research assessment failed or reached its allowance.",
    )
    return checked_patch(
        state,
        {
            "quality_attempts": attempts,
            "stage_error": role,
            "stop_reason": "model_call_limit" if category == "budget" else "fatal_error",
            "tool_errors": {identifier: state["tool_errors"].get(identifier) or record_data(error)},
            **quality_event(state, f"{role}_failed", "Research assessment could not proceed."),
        },
    )
