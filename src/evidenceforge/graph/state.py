"""Typed graph channels plus a validated, JSON-only checkpoint boundary."""

from copy import deepcopy
from typing import Annotated, Literal, Self, cast

from langgraph.types import Overwrite
from pydantic import AwareDatetime, Field, model_validator
from typing_extensions import TypedDict

from evidenceforge.evidence.contracts import Comparison, Proposition, SourceQuality
from evidenceforge.evidence.propositions import compare, extract
from evidenceforge.graph.reducers import (
    RecordData,
    RecordMap,
    merge_calls,
    merge_evidence,
    merge_log,
    merge_query_keys,
    merge_records,
    merge_reservations,
)
from evidenceforge.identity import new_id
from evidenceforge.planning import InitializationResult
from evidenceforge.schemas import (
    ArtifactReference,
    BudgetLimits,
    BudgetReservation,
    CallRecord,
    CitationAuditItem,
    Claim,
    ClaimEvidenceLink,
    ClaimKind,
    ContextReference,
    Contract,
    Count,
    CoverageStatus,
    CriticVerdict,
    EvidenceItem,
    Identifier,
    QuestionCoverage,
    QuestionCoverageStatus,
    RejectedEvidence,
    Report,
    ResearchGap,
    ResearchMessage,
    ResearchQuestion,
    ResearchRequest,
    RunEvent,
    RunStatus,
    SearchQuery,
    SourceAcquisition,
    SourceRecord,
    StopReason,
    SupportVerdict,
    ToolError,
    UsageRecord,
    utc_now,
)


class ResearchState(TypedDict):
    schema_version: int
    run_id: str
    thread_id: str
    owner_scope: str
    request: RecordData
    budget: RecordData
    research_questions: list[RecordData]
    plan_version: int
    approval_status: str
    planning_status: str
    initialization_results: Annotated[RecordMap, merge_records]
    context_refs: list[RecordData]
    search_queries: list[RecordData]
    query_records: Annotated[RecordMap, merge_records]
    attempted_query_keys: Annotated[list[str], merge_query_keys]
    source_records: Annotated[RecordMap, merge_records]
    source_acquisitions: Annotated[RecordMap, merge_records]
    raw_result_refs: Annotated[RecordMap, merge_records]
    evidence_store: Annotated[RecordMap, merge_evidence]
    rejected_evidence: Annotated[RecordMap, merge_records]
    coverage_by_question: dict[str, RecordData]
    coverage_status: str
    source_quality: dict[str, RecordData]
    propositions: RecordMap
    comparisons: RecordMap
    analysis_signature: str | None
    last_analysis_pass: int | None
    analysis_notes: list[str]
    analysis_limited: bool
    gaps: list[RecordData]
    report_claims: RecordMap
    claim_evidence_map: RecordMap
    draft_report: RecordData | None
    critic_verdict: RecordData | None
    citation_audit: list[RecordData]
    final_report: RecordData | None
    quality_attempts: int
    planning_attempts: int
    revision_brief: list[str]
    stage_error: str | None
    coverage_signature: str | None
    last_coverage_pass: int | None
    no_progress_count: int
    unresolved_audits: list[RecordData]
    iteration_count: int
    revision_count: int
    stop_reason: str | None
    run_status: str
    started_at: str
    finished_at: str | None
    reservations: Annotated[RecordMap, merge_reservations]
    usage: Annotated[RecordMap, merge_records]
    calls: Annotated[RecordMap, merge_calls]
    messages: Annotated[RecordMap, merge_log]
    events: Annotated[RecordMap, merge_log]
    tool_errors: Annotated[RecordMap, merge_log]


class StateSnapshot(Contract):
    schema_version: Annotated[int, Field(strict=True, ge=1, le=1)] = 1
    run_id: Identifier
    thread_id: Identifier
    owner_scope: Identifier
    request: ResearchRequest
    budget: BudgetLimits
    research_questions: tuple[ResearchQuestion, ...] = ()
    plan_version: Count = 0
    approval_status: Literal["not_required", "awaiting_approval", "approved", "rejected"] = (
        "not_required"
    )
    planning_status: Literal["not_started", "initializing", "ready", "failed"] = "not_started"
    initialization_results: dict[str, InitializationResult] = Field(default_factory=dict)
    context_refs: tuple[ContextReference, ...] = ()
    search_queries: tuple[SearchQuery, ...] = ()
    query_records: dict[str, SearchQuery] = Field(default_factory=dict)
    attempted_query_keys: tuple[str, ...] = ()
    source_records: dict[str, SourceRecord] = Field(default_factory=dict)
    source_acquisitions: dict[str, SourceAcquisition] = Field(default_factory=dict)
    raw_result_refs: dict[str, ArtifactReference] = Field(default_factory=dict)
    evidence_store: dict[str, EvidenceItem] = Field(default_factory=dict)
    rejected_evidence: dict[str, RejectedEvidence] = Field(default_factory=dict)
    coverage_by_question: dict[str, QuestionCoverage] = Field(default_factory=dict)
    coverage_status: CoverageStatus = CoverageStatus.MISSING
    source_quality: dict[str, SourceQuality] = Field(default_factory=dict)
    propositions: Annotated[dict[str, Proposition], Field(max_length=256)] = Field(
        default_factory=dict
    )
    comparisons: Annotated[dict[str, Comparison], Field(max_length=10000)] = Field(
        default_factory=dict
    )
    analysis_signature: Identifier | None = None
    last_analysis_pass: Count | None = None
    analysis_notes: tuple[str, ...] = ()
    analysis_limited: bool = False
    gaps: tuple[ResearchGap, ...] = ()
    report_claims: dict[str, Claim] = Field(default_factory=dict)
    claim_evidence_map: dict[str, ClaimEvidenceLink] = Field(default_factory=dict)
    draft_report: Report | None = None
    critic_verdict: CriticVerdict | None = None
    citation_audit: tuple[CitationAuditItem, ...] = ()
    final_report: Report | None = None
    quality_attempts: Count = 0
    planning_attempts: Count = 0
    revision_brief: tuple[str, ...] = ()
    stage_error: Identifier | None = None
    coverage_signature: Identifier | None = None
    last_coverage_pass: Count | None = None
    no_progress_count: Count = 0
    unresolved_audits: tuple[CitationAuditItem, ...] = ()
    iteration_count: Count = 0
    revision_count: Count = 0
    stop_reason: StopReason | None = None
    run_status: RunStatus = RunStatus.CREATED
    started_at: AwareDatetime = Field(default_factory=utc_now)
    finished_at: AwareDatetime | None = None
    reservations: dict[str, BudgetReservation] = Field(default_factory=dict)
    usage: dict[str, UsageRecord] = Field(default_factory=dict)
    calls: dict[str, CallRecord] = Field(default_factory=dict)
    messages: Annotated[dict[str, ResearchMessage], Field(max_length=200)] = Field(
        default_factory=dict
    )
    events: Annotated[dict[str, RunEvent], Field(max_length=200)] = Field(default_factory=dict)
    tool_errors: Annotated[dict[str, ToolError], Field(max_length=200)] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        if self.owner_scope != self.request.owner_scope:
            raise ValueError("request scope does not match run scope")
        questions = {question.id for question in self.research_questions}
        if len(questions) != len(self.research_questions):
            raise ValueError("question IDs must be unique")
        if len(questions) > self.budget.max_subquestions:
            raise ValueError("subquestion limit exceeded")
        if len(self.search_queries) > self.budget.max_queries_per_pass:
            raise ValueError("per-pass query limit exceeded")
        if len({query.id for query in self.search_queries}) != len(self.search_queries):
            raise ValueError("pending query IDs must be unique")
        if len(set(self.attempted_query_keys)) != len(self.attempted_query_keys):
            raise ValueError("attempted query keys must be unique")
        if self.iteration_count > self.budget.max_research_passes:
            raise ValueError("retrieval pass limit exceeded")
        if self.quality_attempts + self.planning_attempts > self.budget.max_model_calls:
            raise ValueError("model attempt limit exceeded")
        if self.last_coverage_pass is not None and self.last_coverage_pass > self.iteration_count:
            raise ValueError("coverage cannot precede retrieval")
        if self.revision_count > self.budget.max_rewrites:
            raise ValueError("rewrite limit exceeded")
        if len(self.evidence_store) > self.budget.max_evidence_count:
            raise ValueError("evidence count limit exceeded")
        if sum(len(item.passage.encode("utf-8")) for item in self.evidence_store.values()) > (
            self.budget.max_evidence_bytes
        ):
            raise ValueError("evidence byte limit exceeded")

        maps = (
            self.initialization_results,
            self.query_records,
            self.source_records,
            self.source_acquisitions,
            self.raw_result_refs,
            self.evidence_store,
            self.rejected_evidence,
            self.report_claims,
            self.propositions,
            self.comparisons,
            self.claim_evidence_map,
            self.reservations,
            self.usage,
            self.calls,
            self.messages,
            self.events,
            self.tool_errors,
        )
        for records in maps:
            if any(key != record.id for key, record in records.items()):
                raise ValueError("record map key must match its ID")

        initialization = {
            result.role: result.status for result in self.initialization_results.values()
        }
        if len(initialization) != len(self.initialization_results):
            raise ValueError("initialization roles must be unique")
        if initialization.get("planner") == "unavailable":
            raise ValueError("planner is required")
        if initialization.get("planner") == "ready" and (not questions or self.plan_version == 0):
            raise ValueError("ready planner requires versioned questions")
        if self.planning_status == "ready":
            if initialization.get("planner") != "ready" or initialization.get(
                "context_manager"
            ) not in {
                "ready",
                "unavailable",
            }:
                raise ValueError("planning readiness requires both initialization results")
        if self.planning_status == "failed" and self.run_status != RunStatus.FAILED:
            raise ValueError("failed planning requires failed run status")

        def require(ids: tuple[str, ...], known: object, label: str) -> None:
            if not isinstance(known, (dict, set)):
                raise TypeError("known references must be a registry")
            if any(identifier not in known for identifier in ids):
                raise ValueError(f"unknown {label} reference")

        for context in self.context_refs:
            if context.owner_scope != self.owner_scope:
                raise ValueError("context belongs to a different owner")
        for query in self.query_records.values():
            require(query.question_ids, questions, "question")
            if query.research_pass > self.budget.max_research_passes:
                raise ValueError("query exceeds pass limit")
        for query in self.search_queries:
            if self.query_records.get(query.id) != query:
                raise ValueError("pending query must match its history record")
        for source in self.source_records.values():
            if source.owner_scope is not None and source.owner_scope != self.owner_scope:
                raise ValueError("source belongs to a different owner")
        for acquisition in self.source_acquisitions.values():
            require((acquisition.source_id,), self.source_records, "source")
            require((acquisition.query_id,), self.query_records, "query")
            require((acquisition.snapshot_id,), self.raw_result_refs, "snapshot")
            if self.source_records[acquisition.source_id].content_hash != (
                self.raw_result_refs[acquisition.snapshot_id].content_hash
            ):
                raise ValueError("source content version differs from acquired snapshot")
        for item in self.evidence_store.values():
            if item.owner_scope != self.owner_scope:
                raise ValueError("evidence belongs to a different owner")
            require((item.source_id,), self.source_records, "source")
            require(item.question_ids, questions, "question")
            require(item.acquisition_ids, self.source_acquisitions, "acquisition")
            require((item.locator.snapshot_id,), self.raw_result_refs, "snapshot")
            for acquisition_id in item.acquisition_ids:
                acquisition = self.source_acquisitions[acquisition_id]
                if acquisition.source_id != item.source_id:
                    raise ValueError("evidence/acquisition sources differ")
                if acquisition.snapshot_id != item.locator.snapshot_id:
                    raise ValueError("evidence/acquisition snapshots differ")
        if self.last_analysis_pass is not None and self.last_analysis_pass > self.iteration_count:
            raise ValueError("analysis cannot precede retrieval")
        for sid, ranking in self.source_quality.items():
            if sid != ranking.source_id or sid not in self.source_records:
                raise ValueError("ranking must reference its source")
        parsed_records: dict[str, dict[str, Proposition]] = {}
        for proposition in self.propositions.values():
            require((proposition.evidence_id,), self.evidence_store, "proposition evidence")
            evidence = self.evidence_store[proposition.evidence_id]
            if evidence.id not in parsed_records:
                parsed_records[evidence.id] = {p.id: p for p in extract(evidence)}
            if parsed_records[evidence.id].get(proposition.id) != proposition:
                raise ValueError(
                    "proposition fields must match deterministic extraction of its quote"
                )
            if set(proposition.question_ids) != set(evidence.question_ids):
                raise ValueError("proposition questions differ from its evidence")
            if (
                evidence.passage[proposition.start_offset : proposition.end_offset]
                != proposition.quote
            ):
                raise ValueError("proposition quote differs from the exact evidence span")
        for comparison in self.comparisons.values():
            require(
                (comparison.left_id, comparison.right_id), self.propositions, "compared proposition"
            )
            if (
                compare(
                    self.propositions[comparison.left_id], self.propositions[comparison.right_id]
                )
                != comparison
            ):
                raise ValueError("comparison must match its scoped numeric propositions")
            shared = set(self.propositions[comparison.left_id].question_ids) & set(
                self.propositions[comparison.right_id].question_ids
            )
            if set(comparison.question_ids) != shared:
                raise ValueError("comparison must address the shared questions")
        for rejected in self.rejected_evidence.values():
            if rejected.source_id is not None:
                require((rejected.source_id,), self.source_records, "rejected source")
        for key, coverage in self.coverage_by_question.items():
            if key != coverage.question_id:
                raise ValueError("coverage key must match its question ID")
            require((key,), questions, "coverage question")
            require(coverage.evidence_ids, self.evidence_store, "coverage evidence")
            if any(
                key not in self.evidence_store[eid].question_ids for eid in coverage.evidence_ids
            ):
                raise ValueError("coverage evidence must address that question")
        if self.coverage_status == CoverageStatus.SUFFICIENT:
            if self.analysis_limited or any(
                c.relationship == "contradicts" for c in self.comparisons.values()
            ):
                raise ValueError("sufficiency conflicts with unresolved analysis")
            if not questions or set(self.coverage_by_question) != questions:
                raise ValueError("overall sufficiency requires coverage for every question")
            if any(
                item.status != QuestionCoverageStatus.SUFFICIENT
                for item in self.coverage_by_question.values()
            ):
                raise ValueError("overall sufficiency conflicts with a question gap")
        for gap in self.gaps:
            require((gap.question_id,), questions, "gap question")
        for claim in self.report_claims.values():
            require(claim.question_ids, questions, "claim question")
            require(claim.evidence_ids, self.evidence_store, "claim evidence")
        for link in self.claim_evidence_map.values():
            require((link.claim_id,), self.report_claims, "linked claim")
            require((link.evidence_id,), self.evidence_store, "linked evidence")
        for report in (self.draft_report, self.final_report):
            if report is not None:
                placed = {cid for section in report.sections for cid in section.claim_ids}
                if placed != set(self.report_claims):
                    raise ValueError(
                        "report sections must place exactly the current claim registry"
                    )
                require(report.source_ids, self.source_records, "report source")
                cited_sources = {
                    self.evidence_store[eid].source_id
                    for claim in self.report_claims.values()
                    for eid in claim.evidence_ids
                }
                if set(report.source_ids) != cited_sources:
                    raise ValueError("report sources must match the cited evidence sources")
        if self.critic_verdict is not None:
            if self.draft_report is None or self.critic_verdict.draft_version != (
                self.draft_report.draft_version
            ):
                raise ValueError("critic verdict belongs to a stale or absent draft")
        if len({audit.claim_id for audit in self.citation_audit}) != len(self.citation_audit):
            raise ValueError("one audit item per claim is required")
        for audit in self.citation_audit:
            require((audit.claim_id,), self.report_claims, "audited claim")
            if self.draft_report is None or audit.draft_version != self.draft_report.draft_version:
                raise ValueError("audit belongs to a stale or absent draft")
            if audit.structural_valid:
                require(audit.evidence_ids, self.evidence_store, "audit evidence")
                if set(audit.evidence_ids) != set(self.report_claims[audit.claim_id].evidence_ids):
                    raise ValueError("audit evidence differs from the claim citations")
        if len({item.call_id for item in self.usage.values()}) != len(self.usage):
            raise ValueError("usage must be unique by call ID")
        if len({item.call_id for item in self.reservations.values()}) != len(self.reservations):
            raise ValueError("reservation must be unique by call ID")
        for reservation in self.reservations.values():
            require((reservation.call_id,), self.calls, "reserved call")
        for usage in self.usage.values():
            require((usage.call_id,), self.calls, "usage call")
        for call in self.calls.values():
            if call.response_artifact_id is not None:
                require((call.response_artifact_id,), self.raw_result_refs, "response artifact")
        for error in self.tool_errors.values():
            if error.call_id is not None:
                require((error.call_id,), self.calls, "error call")
            if error.query_id is not None:
                require((error.query_id,), self.query_records, "error query")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("run finish precedes start")
        terminal = {
            RunStatus.COMPLETED,
            RunStatus.PARTIAL,
            RunStatus.INSUFFICIENT_EVIDENCE,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }
        if self.run_status in terminal and (self.finished_at is None or self.stop_reason is None):
            raise ValueError("terminal run requires finish time and stop reason")
        if self.run_status not in terminal and self.finished_at is not None:
            raise ValueError("nonterminal run cannot have finish time")
        if self.run_status == RunStatus.COMPLETED:
            if self.final_report is None or self.coverage_status != CoverageStatus.SUFFICIENT:
                raise ValueError("completed run requires final report and sufficient coverage")
            if self.draft_report != self.final_report or not self.report_claims:
                raise ValueError("completed report must be the audited current nonempty draft")
            if self.critic_verdict is None or self.critic_verdict.decision != "approved":
                raise ValueError("completed run requires critic approval")
            audited = {
                item.claim_id
                for item in self.citation_audit
                if item.structural_valid and item.support == SupportVerdict.SUPPORTED
            }
            factual = {
                claim.id for claim in self.report_claims.values() if claim.kind == ClaimKind.FACT
            }
            if not factual.issubset(audited) or self.stop_reason != StopReason.SUFFICIENT:
                raise ValueError("completed run requires all factual claims supported")
        return self


def validate_state(data: object) -> ResearchState:
    """Validate and copy checkpoint data; reject secrets, clients, extras and invalid references."""
    snapshot = StateSnapshot.model_validate(data)
    return cast(ResearchState, snapshot.model_dump(mode="json"))


def initial_state(request: ResearchRequest, budget: BudgetLimits | None = None) -> ResearchState:
    """Always fresh run/thread IDs, counters, approvals, registries and mutable containers."""
    snapshot = StateSnapshot(
        run_id=new_id("run"),
        thread_id=new_id("thread"),
        owner_scope=request.owner_scope,
        request=request,
        budget=budget or BudgetLimits(),
    )
    return validate_state(snapshot)


_MERGES = {
    "initialization_results": merge_records,
    "query_records": merge_records,
    "source_records": merge_records,
    "source_acquisitions": merge_records,
    "raw_result_refs": merge_records,
    "evidence_store": merge_evidence,
    "rejected_evidence": merge_records,
    "reservations": merge_reservations,
    "usage": merge_records,
    "calls": merge_calls,
    "messages": merge_log,
    "events": merge_log,
    "tool_errors": merge_log,
}
_IMMUTABLE = {"schema_version", "run_id", "thread_id", "owner_scope", "request", "budget"}


def apply_update(state: ResearchState, update: dict[str, object]) -> ResearchState:
    """Pure validated partial update. Singleton fields overwrite; registries use reducers."""
    current = deepcopy(dict(validate_state(state)))
    unknown = set(update) - set(current)
    if unknown:
        raise ValueError(f"unknown state fields: {sorted(unknown)}")
    for key, value in update.items():
        if key in _IMMUTABLE and value != current[key]:
            raise ValueError(f"immutable run field: {key}")
        if isinstance(value, Overwrite):
            if key not in {"messages", "events", "tool_errors"}:
                raise ValueError("explicit reset is only allowed for archived diagnostic logs")
            current[key] = deepcopy(value.value)
        elif key in _MERGES:
            current[key] = _MERGES[key](cast(RecordMap, current[key]), cast(RecordMap, value))
        elif key == "attempted_query_keys":
            current[key] = merge_query_keys(cast(list[str], current[key]), cast(list[str], value))
        else:
            current[key] = deepcopy(value)

    terminal_statuses = {"completed", "partial", "insufficient_evidence", "failed", "cancelled"}
    if state["run_status"] in terminal_statuses:
        for key, value in current.items():
            if key not in {"messages", "events", "tool_errors"} and value != dict(state)[key]:
                raise ValueError("terminal research data is immutable; start a fresh run")
    for counter in (
        "iteration_count",
        "revision_count",
        "plan_version",
        "quality_attempts",
        "planning_attempts",
    ):
        value = current[counter]
        if not isinstance(value, int) or value < cast(int, dict(state)[counter]):
            raise ValueError(f"counter cannot move backwards: {counter}")
    return validate_state(current)
