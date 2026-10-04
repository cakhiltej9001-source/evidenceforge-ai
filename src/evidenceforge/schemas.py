"""Validated, JSON-serializable boundary records. No LLM or retrieval implementation."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    HttpUrl,
    StrictBool,
    StrictInt,
    StringConstraints,
    model_validator,
)


def nonblank(value: str) -> str:
    # Preserve exact evidence whitespace; validate rather than strip.
    if not value.strip():
        raise ValueError("text must contain a non-whitespace character")
    return value


Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_:\-]{0,127}$")]
Text = Annotated[str, StringConstraints(min_length=1, max_length=10_000), AfterValidator(nonblank)]
Passage = Annotated[
    str, StringConstraints(min_length=1, max_length=100_000), AfterValidator(nonblank)
]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
Count = Annotated[StrictInt, Field(ge=0)]
PositiveCount = Annotated[StrictInt, Field(gt=0)]
Nonnegative = Annotated[FiniteFloat, Field(strict=True, ge=0)]
Score = Annotated[FiniteFloat, Field(strict=True, ge=0, le=1)]


def utc_now() -> datetime:
    return datetime.now(UTC)


def unique(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must not contain duplicate IDs")


class Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, validate_default=True, revalidate_instances="always"
    )


class Record(Contract):
    id: Identifier


class SourceType(StrEnum):
    WEB = "web"
    DOCUMENT = "document"
    API = "api"
    MCP = "mcp"
    FIXTURE = "fixture"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    PARTIAL = "partial"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InputStatus(StrEnum):
    ACCEPTED = "accepted"
    NEEDS_CLARIFICATION = "needs_clarification"
    REJECTED = "rejected"


class CoverageStatus(StrEnum):
    MISSING = "missing"
    SUFFICIENT = "sufficient"


class QuestionCoverageStatus(StrEnum):
    MISSING = "missing"
    PARTIAL = "partial"
    SUFFICIENT = "sufficient"
    DISPUTED = "disputed"


class ClaimKind(StrEnum):
    FACT = "fact"
    INFERENCE = "inference"
    RECOMMENDATION = "recommendation"


class Relationship(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONTEXT = "context"
    UNCERTAIN = "uncertain"


class SupportVerdict(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"


class StopReason(StrEnum):
    SUFFICIENT = "sufficient"
    PASS_LIMIT = "pass_limit"
    SEARCH_LIMIT = "search_limit"
    MODEL_CALL_LIMIT = "model_call_limit"
    TOKEN_LIMIT = "token_limit"
    TIME_LIMIT = "time_limit"
    COST_LIMIT = "cost_limit"
    EVIDENCE_LIMIT = "evidence_limit"
    NO_PROGRESS = "no_progress"
    NO_EVIDENCE = "no_evidence"
    REWRITE_LIMIT = "rewrite_limit"
    CANCELLED = "cancelled"
    FATAL_ERROR = "fatal_error"
    RECURSION_LIMIT = "recursion_limit"
    PERSISTENCE_FAILURE = "persistence_failure"


class BudgetLimits(Contract):
    max_research_passes: PositiveCount = 3
    max_rewrites: Count = 2
    max_subquestions: PositiveCount = 8
    max_queries_per_pass: PositiveCount = 4
    max_searches: PositiveCount = 12
    max_model_calls: PositiveCount = 32
    reserved_quality_calls: PositiveCount = 3
    max_total_tokens: PositiveCount = 100_000
    max_evidence_count: PositiveCount = 200
    max_evidence_bytes: PositiveCount = 1_000_000
    max_elapsed_seconds: PositiveCount = 1800
    max_concurrency: PositiveCount = 3
    max_attempts_per_call: PositiveCount = 3
    max_cost_usd: Nonnegative | None = None

    @model_validator(mode="after")
    def quality_capacity(self) -> Self:
        if self.reserved_quality_calls > self.max_model_calls:
            raise ValueError("reserved quality calls exceed total model allowance")
        return self


class ResearchRequest(Contract):
    question: Text
    owner_scope: Identifier = "local"
    mode: Annotated[str, StringConstraints(pattern=r"^(quick|deep|academic)$")] = "deep"
    language: Text = "en"
    document_ids: Annotated[tuple[Identifier, ...], Field(max_length=64)] = ()
    preferences: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def documents_unique(self) -> Self:
        unique(self.document_ids, "document_ids")
        return self


class InputDecision(Contract):
    status: InputStatus
    reason: Text


class ResearchQuestion(Record):
    question: Text
    acceptance_criteria: Annotated[tuple[Text, ...], Field(min_length=1)]
    importance: Annotated[FiniteFloat, Field(strict=True, gt=0, le=1)] = 1.0


class ContextReference(Record):
    owner_scope: Identifier
    kind: Annotated[str, StringConstraints(pattern=r"^(document|prior_report)$")]
    target_id: Identifier


class SearchQuery(Record):
    question_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    text: Text
    source_type: SourceType
    research_pass: PositiveCount
    purpose: Annotated[
        str, StringConstraints(pattern=r"^(support|counter_evidence|primary_source)$")
    ] = "support"

    @model_validator(mode="after")
    def questions_unique(self) -> Self:
        unique(self.question_ids, "question_ids")
        return self


class SourceRecord(Record):
    primary_evidence: StrictBool | None = None
    methodology_transparent: StrictBool | None = None
    metadata_rationale: Text | None = None
    title: Text
    source_type: SourceType
    provider: Text
    content_hash: Digest
    url: HttpUrl | None = None
    document_id: Identifier | None = None
    document_hash: Digest | None = None
    chunk_id: Identifier | None = None
    owner_scope: Identifier | None = None
    publisher: Text | None = None
    publication_date: Text | None = None
    source_family: Identifier | None = None
    access_status: Annotated[
        str, StringConstraints(pattern=r"^(available|excerpt_only|inaccessible|failed)$")
    ] = "available"

    @model_validator(mode="after")
    def location_required(self) -> Self:
        if (
            self.primary_evidence is not None or self.methodology_transparent is not None
        ) and self.metadata_rationale is None:
            raise ValueError("ranking metadata requires an explicit rationale")
        if self.url is not None and (
            self.url.username is not None or self.url.password is not None
        ):
            raise ValueError("source URLs must not contain credentials")
        if self.source_type == SourceType.DOCUMENT:
            if self.document_id is None or self.owner_scope is None:
                raise ValueError("document sources require document_id and owner_scope")
            if self.url is not None:
                raise ValueError("document sources use private locators rather than public URLs")
        elif self.source_type in (SourceType.WEB, SourceType.API, SourceType.MCP):
            if self.url is None:
                raise ValueError("remote sources require an HTTP(S) URL")
        return self


class SourceAcquisition(Record):
    page: PositiveCount | None = None
    paragraph: PositiveCount | None = None
    section: Text | None = None
    document_start_offset: Count | None = None
    document_end_offset: Count | None = None
    source_id: Identifier
    query_id: Identifier
    snapshot_id: Identifier
    retrieved_at: AwareDatetime
    content_scope: Annotated[
        str, StringConstraints(pattern=r"^(full_text|search_excerpt|structured_response)$")
    ]


class ArtifactReference(Record):
    content_hash: Digest
    storage_key: Text
    parser_version: Text
    byte_count: Count

    @model_validator(mode="after")
    def relative_storage_key(self) -> Self:
        key = self.storage_key.replace("\\", "/")
        if (
            key.startswith("/")
            or ":" in key
            or any(part in ("", ".", "..") for part in key.split("/"))
        ):
            raise ValueError("storage_key must be a relative artifact key without traversal")
        return self


class EvidenceLocator(Contract):
    document_start_offset: Count | None = None
    document_end_offset: Count | None = None
    snapshot_id: Identifier
    start_offset: Count | None = None
    end_offset: Count | None = None
    page: PositiveCount | None = None
    paragraph: PositiveCount | None = None
    section: Text | None = None

    @model_validator(mode="after")
    def complete_locator(self) -> Self:
        if (self.document_start_offset is None) != (self.document_end_offset is None):
            raise ValueError("document offsets must be paired")
        if self.document_start_offset is not None and self.document_end_offset is not None:
            if self.document_end_offset <= self.document_start_offset:
                raise ValueError("document offsets must increase")
        if (self.start_offset is None) != (self.end_offset is None):
            raise ValueError("start_offset and end_offset must be supplied together")
        if self.start_offset is not None and self.end_offset is not None:
            if self.end_offset <= self.start_offset:
                raise ValueError("end_offset must exceed start_offset")
        if self.start_offset is None and self.page is None and self.paragraph is None:
            if self.section is None:
                raise ValueError("evidence requires an offset, page, paragraph or section locator")
        return self


class EvidenceItem(Record):
    source_id: Identifier
    owner_scope: Identifier
    acquisition_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    question_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    passage: Passage
    locator: EvidenceLocator
    relevance: Score
    relevance_rationale: Text

    @model_validator(mode="after")
    def provenance_unique(self) -> Self:
        unique(self.acquisition_ids, "acquisition_ids")
        unique(self.question_ids, "question_ids")
        if self.locator.start_offset is not None and self.locator.end_offset is not None:
            if self.locator.end_offset - self.locator.start_offset != len(self.passage):
                raise ValueError("character offset length must equal the exact passage length")
        return self


class RejectedEvidence(Record):
    candidate_id: Identifier
    source_id: Identifier | None = None
    reason: Annotated[
        str,
        StringConstraints(
            pattern=r"^(irrelevant|duplicate|no_locator|parse_failed|suspected_instruction_attack|evidence_limit|content_limit|snapshot_limit|unavailable_content)$"
        ),
    ]
    rationale: Text


class ResearchGap(Record):
    purpose: Annotated[
        str, StringConstraints(pattern=r"^(support|counter_evidence|primary_source)$")
    ] = "support"
    question_id: Identifier
    missing_aspect: Text
    needed_source_types: tuple[SourceType, ...] = ()
    recommended_query: Text
    priority: Score = 1.0


class QuestionCoverage(Contract):
    question_id: Identifier
    status: QuestionCoverageStatus
    evidence_ids: tuple[Identifier, ...] = ()
    rationale: Text

    @model_validator(mode="after")
    def supported_coverage(self) -> Self:
        unique(self.evidence_ids, "evidence_ids")
        if self.status == QuestionCoverageStatus.SUFFICIENT and not self.evidence_ids:
            raise ValueError("sufficient coverage requires evidence")
        return self


class Claim(Record):
    statement: Text
    kind: ClaimKind
    question_ids: tuple[Identifier, ...] = ()
    evidence_ids: tuple[Identifier, ...] = ()
    qualifiers: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def links_unique(self) -> Self:
        unique(self.question_ids, "question_ids")
        unique(self.evidence_ids, "evidence_ids")
        # Empty citations are allowed in a draft so the later auditor can identify omissions.
        return self


class ClaimEvidenceLink(Record):
    claim_id: Identifier
    evidence_id: Identifier
    relationship: Relationship
    rationale: Text
    verifier: Text


class ReportSection(Contract):
    name: Annotated[
        str, StringConstraints(pattern=r"^(summary|key_findings|limitations|disagreements)$")
    ]
    claim_ids: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def claims_unique(self) -> Self:
        unique(self.claim_ids, "claim_ids")
        return self


class Report(Record):
    draft_version: PositiveCount
    sections: tuple[ReportSection, ...]
    source_ids: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def required_sections(self) -> Self:
        names = tuple(section.name for section in self.sections)
        if len(names) != len(set(names)):
            raise ValueError("report sections must be unique")
        if not {"summary", "key_findings"}.issubset(names):
            raise ValueError("report requires summary and key_findings sections")
        unique(self.source_ids, "source_ids")
        # Sources are rendered from source_ids, not from model-generated URLs.
        return self


class CriticVerdict(Contract):
    draft_version: PositiveCount
    decision: Annotated[str, StringConstraints(pattern=r"^(approved|revise)$")]
    revision_brief: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def actionable_revision(self) -> Self:
        if self.decision == "revise" and not self.revision_brief:
            raise ValueError("revision requires a concrete brief")
        return self


class CitationAuditItem(Record):
    draft_version: PositiveCount
    claim_id: Identifier
    evidence_ids: tuple[Identifier, ...] = ()
    structural_valid: StrictBool
    support: SupportVerdict
    rationale: Text
    repair_action: Text | None = None

    @model_validator(mode="after")
    def supported_citation(self) -> Self:
        unique(self.evidence_ids, "evidence_ids")
        if self.support == SupportVerdict.SUPPORTED:
            if not self.structural_valid or not self.evidence_ids:
                raise ValueError("supported audit requires valid referenced evidence")
        return self


class ToolError(Record):
    provider: Text
    query_id: Identifier | None = None
    call_id: Identifier | None = None
    category: Annotated[
        str,
        StringConstraints(
            pattern=r"^(authentication|rate_limit|timeout|parse|schema|provider|budget|cancelled|internal)$"
        ),
    ]
    retryable: StrictBool
    attempt: PositiveCount
    message: Text
    occurred_at: AwareDatetime = Field(default_factory=utc_now)


class BudgetReservation(Record):
    call_id: Identifier
    searches: Count = 0
    model_calls: Count = 0
    tokens: Count = 0
    estimated_cost_usd: Nonnegative | None = None
    status: Annotated[str, StringConstraints(pattern=r"^(reserved|settled|released)$")] = "reserved"


class UsageRecord(Record):
    call_id: Identifier
    provider: Text
    model: Text | None = None
    input_tokens: Count | None = None
    output_tokens: Count | None = None
    search_credits: Nonnegative | None = None
    latency_ms: Nonnegative
    estimated_cost_usd: Nonnegative | None = None
    price_table_version: Text | None = None

    @model_validator(mode="after")
    def dated_cost(self) -> Self:
        if self.estimated_cost_usd is not None and self.price_table_version is None:
            raise ValueError("known cost estimates require a price-table version")
        return self


class CallRecord(Record):
    revision: PositiveCount = 1
    request_hash: Digest
    provider: Text
    kind: Annotated[str, StringConstraints(pattern=r"^(model|search|extraction)$")]
    status: Annotated[
        str, StringConstraints(pattern=r"^(pending|completed|failed|ambiguous|cancelled)$")
    ]
    started_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    response_artifact_id: Identifier | None = None

    @model_validator(mode="after")
    def completion(self) -> Self:
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at precedes started_at")
        if self.status == "completed":
            if self.finished_at is None or self.response_artifact_id is None:
                raise ValueError("completed calls require a finish time and recorded response")
        if self.status in ("failed", "cancelled") and self.finished_at is None:
            raise ValueError("finished calls require a finish time")
        if self.status == "pending" and self.finished_at is not None:
            raise ValueError("pending calls cannot have a finish time")
        return self


class RunEvent(Record):
    kind: Text
    message: Text
    related_ids: tuple[Identifier, ...] = ()
    occurred_at: AwareDatetime = Field(default_factory=utc_now)


class ResearchMessage(Record):
    role: Annotated[str, StringConstraints(pattern=r"^(user|assistant|system)$")]
    content: Text
    occurred_at: AwareDatetime = Field(default_factory=utc_now)
