"""Allowlisted public progress events and opt-in LangSmith custom spans."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.schemas import RunStatus, StopReason


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
        return {
            "run_status": self.run_status,
            "stop_reason": self.stop_reason,
            "retrieval_passes": self.retrieval_passes,
            "rewrites": self.rewrites,
            "search_calls": self.search_calls,
            "evidence_count": self.evidence_count,
            "tool_errors": self.tool_errors,
            "citation_checks": self.citation_checks,
        }


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
    """Send only allowlisted counters and verify server receipt without graph payloads."""

    def __init__(self, client: object, project_name: str, *, max_receipts: int = 256) -> None:
        if not project_name.strip() or max_receipts < 1:
            raise ValueError("A trace project and positive receipt limit are required.")
        self.client = client
        self.project_name = project_name
        self.max_receipts = max_receipts
        self._receipts: dict[UUID, tuple[str, dict[str, str | int | None], datetime]] = {}
        self._verified: set[UUID] = set()
        self._omitted = 0

    @classmethod
    def from_api_key(cls, api_key: str, project_name: str) -> "LangSmithTraceSink":
        """Explicit opt-in client with one hosted endpoint and no background tracing."""
        from langsmith import Client
        from urllib3.util.retry import Retry

        if not api_key.strip():
            raise ValueError("A LangSmith API key is required.")
        client = Client(
            api_url="https://api.smith.langchain.com",
            api_key=api_key.strip(),
            auto_batch_tracing=False,
            timeout_ms=(2000, 3000),
            retry_config=Retry(total=0),
            hide_inputs=True,
            hide_outputs=False,
            hide_metadata=True,
            omit_traced_runtime_info=True,
            tracing_mode="langsmith",
            tracing_sampling_rate=1.0,
        )
        return cls(client, project_name)

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
        if not isinstance(progress, PublicProgress):
            raise ValueError("A public counter snapshot is required.")
        if type(progress.run_status) is not str or (
            progress.stop_reason is not None and type(progress.stop_reason) is not str
        ):
            raise ValueError("Trace statuses must be allowlisted strings.")
        RunStatus(progress.run_status)
        if progress.stop_reason is not None:
            StopReason(progress.stop_reason)
        outputs = PublicProgress.as_dict(progress)
        for field, value in outputs.items():
            if field not in {"run_status", "stop_reason"} and (type(value) is not int or value < 0):
                raise ValueError("Trace counters must be nonnegative integers.")
        run_id, at = uuid4(), datetime.now(UTC)
        self.client.create_run(  # type: ignore[attr-defined]
            name=f"evidenceforge.{phase}",
            inputs={},
            outputs=outputs,
            run_type="chain",
            id=run_id,
            project_name=self.project_name,
            start_time=at,
            end_time=at,
        )
        if len(self._receipts) < self.max_receipts:
            self._receipts[run_id] = (f"evidenceforge.{phase}", outputs, at)
        else:
            self._omitted += 1

    def verify_delivery(self, *, max_readbacks: int = 32) -> dict[str, int | bool]:
        """Read only our UUID receipts; SDK acceptance alone is not delivery."""
        if max_readbacks < 1:
            raise ValueError("A positive readback limit is required.")
        pending = [key for key in self._receipts if key not in self._verified]
        try:
            project = self.client.read_project(  # type: ignore[attr-defined]
                project_name=self.project_name
            )
        except Exception:
            project = None
        if project is not None:
            for run_id in pending[:max_readbacks]:
                name, outputs, at = self._receipts[run_id]
                try:
                    # The pinned SDK keeps read_run; project/start also work on
                    # SmithDB-only backends. No child runs are requested.
                    stored: Any = self.client.read_run(  # type: ignore[attr-defined]
                        run_id, project_id=project.id, start_time=at
                    )
                    if (
                        stored.id == run_id
                        and stored.name == name
                        and stored.inputs == {}
                        and stored.outputs == outputs
                        and stored.end_time is not None
                        and stored.session_id == project.id
                    ):
                        self._verified.add(run_id)
                except Exception:
                    # Remote errors may include private values; retain no error text.
                    continue
        tracked = len(self._receipts)
        return {
            "tracked_receipts": tracked,
            "verified_receipts": len(self._verified),
            "unverified_receipts": tracked - len(self._verified),
            "omitted_receipts": self._omitted,
            "remote_delivery_verified": bool(tracked)
            and len(self._verified) == tracked
            and self._omitted == 0,
        }

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if close is not None:
            close()


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
