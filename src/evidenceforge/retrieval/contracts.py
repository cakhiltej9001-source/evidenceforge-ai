"""Validated retrieval results and limits; responses never carry credentials."""

import ipaddress
from typing import Annotated, Literal, Protocol, Self

from pydantic import AwareDatetime, Field, HttpUrl, StrictBool, model_validator

from evidenceforge.schemas import (
    ArtifactReference,
    BudgetReservation,
    CallRecord,
    Contract,
    Count,
    Digest,
    Identifier,
    Nonnegative,
    PositiveCount,
    Score,
    SearchQuery,
    SourceType,
    Text,
    UsageRecord,
    utc_now,
)

ErrorCategory = Literal[
    "authentication", "rate_limit", "timeout", "schema", "provider", "budget", "internal"
]


class RetrievalFailure(RuntimeError):
    def __init__(self, category: ErrorCategory, retry_after_seconds: float | None = None) -> None:
        self.category = category
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Retrieval operation failed.")


class ArtifactFailure(RuntimeError):
    """Missing, corrupt, oversized or inaccessible retained artifact."""


class RetrievalOptions(Contract):
    structured_domain_filters: StrictBool = Field(default=False, exclude_if=lambda value: not value)
    max_results: Annotated[PositiveCount, Field(le=20)] = 5
    max_response_bytes: Annotated[PositiveCount, Field(le=10_000_000)] = 1_000_000
    max_source_bytes: Annotated[PositiveCount, Field(le=1_000_000)] = 100_000
    max_artifact_bytes: PositiveCount = 16_000_000
    timeout_seconds: Annotated[float, Field(gt=0, le=60, allow_inf_nan=False)] = 30.0
    passage_chars: Annotated[PositiveCount, Field(le=100_000)] = 1000
    max_passages_per_source: Annotated[PositiveCount, Field(le=100)] = 8
    min_relevance: Score = 0.15


class RetrievedSource(Contract):
    publisher: Text | None = None
    publication_date: Text | None = None
    source_family: Identifier | None = None
    primary_evidence: StrictBool | None = None
    methodology_transparent: StrictBool | None = None
    metadata_rationale: Text | None = None
    title: Text
    url: HttpUrl
    content: Annotated[str, Field(max_length=1_000_000)]
    source_type: SourceType = SourceType.WEB
    owner_scope: Identifier | None = None
    content_scope: Literal["full_text", "search_excerpt"] = "full_text"

    @model_validator(mode="after")
    def public_web_boundary(self) -> Self:
        if (
            self.primary_evidence is not None or self.methodology_transparent is not None
        ) and self.metadata_rationale is None:
            raise ValueError("ranking metadata requires an explicit rationale")
        if self.url.username is not None or self.url.password is not None:
            raise ValueError("source URL contains credentials")
        host = (self.url.host or "").rstrip(".")
        try:
            address = ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            address = None
        if (
            host.lower() == "localhost"
            or host.lower().endswith(".localhost")
            or host.lower().endswith(".local")
            or host.lower().endswith(".internal")
            or (address is not None and not address.is_global)
        ):
            raise ValueError("source URL is not public")
        if (
            self.source_type not in (SourceType.WEB, SourceType.API, SourceType.MCP)
            or self.owner_scope is not None
        ):
            raise ValueError("External results must be public sources")
        return self


class RetrievedDocument(Contract):
    title: Text
    url: None = None
    source_type: Literal[SourceType.DOCUMENT] = SourceType.DOCUMENT
    owner_scope: Identifier
    document_id: Identifier
    document_hash: Digest
    chunk_id: Identifier
    content: Annotated[str, Field(min_length=1, max_length=100_000)]
    content_scope: Literal["full_text"] = "full_text"
    document_start_offset: Count
    document_end_offset: PositiveCount
    page: PositiveCount | None = None
    paragraph: PositiveCount | None = None
    section: Text | None = None

    @model_validator(mode="after")
    def located(self) -> Self:
        if self.document_end_offset - self.document_start_offset != len(self.content):
            raise ValueError("document result offsets differ from chunk length")
        if self.page is None and self.paragraph is None:
            raise ValueError("document result requires a page or paragraph")
        return self


class RetrievalBatch(Contract):
    results: Annotated[tuple[RetrievedSource | RetrievedDocument, ...], Field(max_length=20)] = ()
    retrieved_at: AwareDatetime = Field(default_factory=utc_now)
    search_credits: Nonnegative | None = None


class RetrievalAdapter(Protocol):
    name: str
    is_live: bool

    async def search(self, query: SearchQuery, options: RetrievalOptions) -> object: ...


class CallReceipt(Contract):
    owner_scope: Identifier
    run_id: Identifier
    call: CallRecord
    reservation: BudgetReservation
    response: ArtifactReference | None = None
    usage: UsageRecord | None = None
    error_category: ErrorCategory | None = None

    @model_validator(mode="after")
    def consistent_receipt(self) -> Self:
        if self.reservation.call_id != self.call.id:
            raise ValueError("receipt reservation belongs to another call")
        if self.usage is not None and self.usage.call_id != self.call.id:
            raise ValueError("receipt usage belongs to another call")
        if self.call.status == "completed":
            if self.response is None or self.call.response_artifact_id != self.response.id:
                raise ValueError("completed receipt requires its retained response")
        return self
