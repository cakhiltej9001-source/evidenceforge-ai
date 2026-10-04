"""Allowlisted public progress events and opt-in LangSmith custom spans."""

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from evidenceforge.graph.state import ResearchState, StateSnapshot


@dataclass(frozen=True)
class PublicProgress:
    run_status: str
    stop_reason: str | None
    retrieval_passes: int
    rewrites: int
    search_calls: int
    evidence_count: int
    tool_errors: int
    citation_checks: int

    def as_dict(self) -> dict[str, str | int | None]:
        return dict(self.__dict__)


def public_progress(state: ResearchState) -> PublicProgress:
    s = StateSnapshot.model_validate(state)
    return PublicProgress(
        run_status=s.run_status.value,
        stop_reason=s.stop_reason.value if s.stop_reason else None,
        retrieval_passes=s.iteration_count,
        rewrites=s.revision_count,
        search_calls=len(s.calls),
        evidence_count=len(s.evidence_store),
        tool_errors=len(s.tool_errors),
        citation_checks=len(s.citation_audit),
    )


class TraceSink(Protocol):
    def emit(self, phase: str, progress: PublicProgress) -> None: ...


class LangSmithTraceSink:
    """Send only allowlisted counters; never pass graph state or source text."""

    def __init__(self, client: object, project_name: str) -> None:
        self.client = client
        self.project_name = project_name

    def emit(self, phase: str, progress: PublicProgress) -> None:
        if phase not in {
            "progress",
            "retrieval",
            "rewrite",
            "tool_failure",
            "budget_stop",
            "audit",
            "final",
            "cancelled",
        }:
            raise ValueError("Unsupported trace phase")
        # The installed LangSmith Client accepts create_run(name, inputs, run_type, id).
        self.client.create_run(  # type: ignore[attr-defined]
            name=f"evidenceforge.{phase}",
            inputs={},
            outputs=progress.as_dict(),
            run_type="chain",
            id=uuid4(),
            project_name=self.project_name,
        )


def trace_phase(previous: PublicProgress, current: PublicProgress) -> str:
    if (
        current.stop_reason
        in {
            "model_call_limit",
            "search_limit",
            "time_limit",
            "cost_limit",
            "token_limit",
        }
        and previous.stop_reason != current.stop_reason
    ):
        return "budget_stop"
    if current.tool_errors > previous.tool_errors:
        return "tool_failure"
    if current.rewrites > previous.rewrites:
        return "rewrite"
    if current.citation_checks > previous.citation_checks:
        return "audit"
    if current.retrieval_passes > previous.retrieval_passes:
        return "retrieval"
    return "progress"


_EVENT_LABELS = {
    "initialization_started": "Planning started",
    "plan_created": "Plan created",
    "plan_edited": "Plan edited",
    "plan_approved": "Plan approved",
    "plan_rejected": "Plan rejected",
    "context_selected": "Context checked",
    "queries_generated": "Queries created",
    "retrieval_batch_completed": "Retrieval pass completed",
    "evidence_extraction_completed": "Evidence extracted",
    "coverage": "Coverage assessed",
    "coverage_evaluator": "Coverage assessed",
    "synthesis": "Report drafted",
    "critic": "Report reviewed",
    "citation_checker": "Citations checked",
    "finalizer": "Research finalized",
    "rewrite": "Report revision reserved",
    "evidence_intelligence": "Evidence compared",
}


def public_timeline(state: ResearchState) -> list[dict[str, str]]:
    """Reconnect-safe labels derived from retained events, never raw messages."""
    s = StateSnapshot.model_validate(state)
    result = []
    for event in s.events.values():
        label = _EVENT_LABELS.get(event.kind)
        if label is None and event.kind.endswith("_failed"):
            label = "Workflow step unavailable"
        if label is not None:
            result.append({"id": event.id, "time": event.occurred_at.isoformat(), "step": label})
    return sorted(result, key=lambda item: (item["time"], item["id"]))[-100:]
