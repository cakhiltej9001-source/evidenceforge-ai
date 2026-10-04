"""Shared boundary/error helpers; emit only fixed public diagnostics and counts."""

from typing import cast

from evidenceforge.graph.reducers import RecordData
from evidenceforge.graph.state import ResearchState, apply_update
from evidenceforge.identity import stable_id
from evidenceforge.planning import InitializationResult
from evidenceforge.schemas import Contract, RunEvent, ToolError, utc_now

Update = dict[str, object]


def record_data(record: Contract) -> RecordData:
    return cast(RecordData, record.model_dump(mode="json"))


def checked_patch(state: ResearchState, update: Update) -> Update:
    validated = dict(apply_update(state, update))
    return {key: validated[key] for key in update}


def event_patch(state: ResearchState, role: str, kind: str, message: str) -> Update:
    event_id = stable_id(
        "event", state["run_id"], role, kind, state["iteration_count"], state["revision_count"]
    )
    existing = state["events"].get(event_id)
    payload = existing or record_data(RunEvent(id=event_id, kind=kind, message=message))
    return {"events": {event_id: payload}}


def initialization_patch(state: ResearchState, role: str, status: str) -> Update:
    result = InitializationResult(
        id=stable_id("initialization", state["run_id"], role),
        role=role,
        status=status,
    )
    return {"initialization_results": {result.id: record_data(result)}}


def failure_patch(
    state: ResearchState,
    role: str,
    category: str,
    *,
    optional: bool = False,
) -> Update:
    messages = {
        "schema": "Structured output failed validation.",
        "timeout": "The configured node timeout was reached.",
        "provider": "The configured adapter is unavailable.",
        "budget": "Planning reached a configured allowance.",
    }
    error_id = stable_id("error", state["run_id"], role, category)
    payload = state["tool_errors"].get(error_id) or record_data(
        ToolError(
            id=error_id,
            provider=role,
            category=category,
            retryable=False,
            attempt=1,
            message=messages[category],
        )
    )
    update: Update = {
        "tool_errors": {error_id: payload},
        **event_patch(state, role, f"{role}_failed", messages[category]),
    }
    if role in ("planner", "context_manager"):
        update.update(initialization_patch(state, role, "unavailable" if optional else "failed"))
    else:
        update.update(
            {
                "planning_status": "failed",
                "run_status": "failed",
                "stop_reason": "fatal_error",
                "finished_at": utc_now().isoformat(),
            }
        )
    return checked_patch(state, update)
