"""Dedicated, side-effect-free plan interrupt before queries or retrieval."""

from typing import Annotated

from langgraph.types import interrupt
from pydantic import Field

from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.identity import stable_id
from evidenceforge.nodes.common import Update, checked_patch, record_data
from evidenceforge.schemas import Contract, PositiveCount, RunEvent, utc_now


class PlanDecision(Contract):
    approved: Annotated[bool, Field(strict=True)]
    plan_version: PositiveCount


def prepare_approval(state: ResearchState, required: bool) -> Update:
    s = StateSnapshot.model_validate(state)
    statuses = {r.role: r.status for r in s.initialization_results.values()}
    if s.run_status != "running":
        return {}
    if "failed" in statuses.values():
        return checked_patch(
            state,
            {
                "run_status": "failed",
                "planning_status": "failed",
                "stop_reason": "fatal_error",
                "finished_at": utc_now().isoformat(),
            },
        )
    if not s.research_questions:
        return {}
    return checked_patch(
        state, {"approval_status": "awaiting_approval" if required else "not_required"}
    )


def approve_plan(state: ResearchState) -> Update:
    s = StateSnapshot.model_validate(state)
    if s.approval_status != "awaiting_approval":
        return {}
    # This node restarts on resume. No model calls, writes or counters precede interrupt.
    decision = PlanDecision.model_validate(
        interrupt(
            {
                "kind": "plan_approval",
                "plan_version": s.plan_version,
                "questions": [q.model_dump(mode="json") for q in s.research_questions],
            }
        )
    )
    if decision.plan_version != s.plan_version:
        raise ValueError("Approval does not match the current plan version.")
    event = RunEvent(
        id=stable_id("plan_decision", s.run_id, s.plan_version),
        kind="plan_approved" if decision.approved else "plan_rejected",
        message="The current plan decision was recorded.",
    )
    if decision.approved:
        return checked_patch(
            state, {"approval_status": "approved", "events": {event.id: record_data(event)}}
        )
    return checked_patch(
        state,
        {
            "events": {event.id: record_data(event)},
            "approval_status": "rejected",
            "run_status": "cancelled",
            "stop_reason": "cancelled",
            "finished_at": utc_now().isoformat(),
        },
    )


def after_approval(state: ResearchState) -> str:
    s = StateSnapshot.model_validate(state)
    if (
        s.run_status != "running"
        or not s.research_questions
        or any(result.status == "failed" for result in s.initialization_results.values())
    ):
        return "finalizer"
    return "query_generator"
