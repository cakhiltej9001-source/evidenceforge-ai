"""Deterministic run initialization; both dependent branches start from one snapshot."""

from evidenceforge.graph.state import ResearchState, validate_state
from evidenceforge.nodes.common import Update, checked_patch, event_patch
from evidenceforge.planning import PlanningContractError


def manager(state: ResearchState) -> Update:
    state = validate_state(state)
    if (
        state["run_status"] != "created"
        or state["planning_status"] != "not_started"
        or state["research_questions"]
        or state["initialization_results"]
        or state["query_records"]
        or state["context_refs"]
        or state["source_quality"]
        or state["propositions"]
        or state["comparisons"]
        or state["analysis_signature"]
        or state["analysis_notes"]
        or state["analysis_limited"]
        or state["last_analysis_pass"] is not None
        or state["evidence_store"]
        or state["planning_attempts"]
        or state["plan_version"]
        or state["iteration_count"]
        or state["revision_count"]
        or state["attempted_query_keys"]
        or state["source_records"]
        or state["reservations"]
        or state["calls"]
        or state["usage"]
        or state["draft_report"]
        or state["final_report"]
        or state["stop_reason"]
    ):
        raise PlanningContractError("initialization requires a fresh run")
    return checked_patch(
        state,
        {
            "run_status": "running",
            "planning_status": "initializing",
            **event_patch(
                state, "manager", "initialization_started", "Structured planning started."
            ),
        },
    )
