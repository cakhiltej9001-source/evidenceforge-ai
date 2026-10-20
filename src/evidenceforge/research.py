"""Structured research inputs and validated model-output boundaries."""

from datetime import date
from typing import Annotated, Literal, Protocol, runtime_checkable

from pydantic import Field, StrictBool

from evidenceforge.evidence.contracts import AnalysisOptions, Comparison, Proposition, SourceQuality
from evidenceforge.evidence.deduplication import DuplicateEvidence
from evidenceforge.models.base import PlanningModel
from evidenceforge.schemas import (
    Claim,
    ClaimKind,
    Contract,
    Count,
    EvidenceItem,
    Identifier,
    PositiveCount,
    QuestionCoverage,
    Report,
    ResearchGap,
    ResearchQuestion,
    ResearchRequest,
    Text,
)


class CriterionSupport(Contract):
    index: Count
    evidence_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]


class QuestionAssessment(Contract):
    question_id: Identifier
    criteria: tuple[CriterionSupport, ...] = ()


class CoverageAssessment(Contract):
    questions: Annotated[tuple[QuestionAssessment, ...], Field(min_length=1, max_length=32)]


class CoverageInput(Contract):
    duplicate_evidence: tuple[DuplicateEvidence, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    questions: tuple[ResearchQuestion, ...]
    evidence: tuple[EvidenceItem, ...]


class CoverageCriterion(Contract):
    id: Identifier
    question_id: Identifier
    text: Text


class CoverageSelectionInput(Contract):
    questions: tuple[ResearchQuestion, ...]
    criteria: tuple[CoverageCriterion, ...]
    evidence: tuple[EvidenceItem, ...]


class CoverageMatch(Contract):
    criterion_id: Identifier
    evidence_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]


class CoverageSelectionDraft(Contract):
    matches: Annotated[tuple[CoverageMatch, ...], Field(max_length=256)]


class DraftClaim(Contract):
    statement: Text
    question_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    evidence_ids: tuple[Identifier, ...] = ()
    kind: ClaimKind = ClaimKind.FACT
    qualifiers: tuple[Text, ...] = ()
    section: Literal["summary", "key_findings", "limitations", "disagreements"] = "key_findings"


class ReportDraft(Contract):
    claims: Annotated[tuple[DraftClaim, ...], Field(min_length=1, max_length=64)]


class QuoteSelection(Contract):
    evidence_id: Identifier
    question_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    section: Literal["summary", "key_findings", "limitations", "disagreements"] = "key_findings"


class QuoteSelectionDraft(Contract):
    """Select retained passages; the model never writes or edits their wording."""

    claims: Annotated[tuple[QuoteSelection, ...], Field(min_length=1, max_length=64)]


class SynthesisInput(Contract):
    reference_date: date | None = Field(default=None, exclude_if=lambda value: value is None)
    duplicate_evidence: tuple[DuplicateEvidence, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    source_quality: tuple[SourceQuality, ...] = ()
    propositions: tuple[Proposition, ...] = ()
    comparisons: tuple[Comparison, ...] = ()
    request: ResearchRequest
    questions: tuple[ResearchQuestion, ...]
    evidence: tuple[EvidenceItem, ...]
    gaps: tuple[ResearchGap, ...]
    revision_brief: tuple[Text, ...]
    draft_version: PositiveCount


class CriticInput(Contract):
    reference_date: date | None = Field(default=None, exclude_if=lambda value: value is None)
    request: ResearchRequest | None = Field(default=None, exclude_if=lambda value: value is None)
    questions: tuple[ResearchQuestion, ...] = Field(default=(), exclude_if=lambda value: not value)
    duplicate_evidence: tuple[DuplicateEvidence, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    report: Report
    claims: tuple[Claim, ...]
    evidence: tuple[EvidenceItem, ...]
    coverage: tuple[QuestionCoverage, ...]


class CriticAssessment(Contract):
    decision: Literal["approved", "revise"]
    revision_brief: tuple[Text, ...] = ()


class ResearchOptions(Contract):
    production_policy_version: Literal[0, 1, 2, 3, 4, 5, 6] = 0
    require_plan_approval: bool = False
    live_web: StrictBool = False
    live_energy: StrictBool = False
    quality_input_version: Literal[1, 2] = 2
    quote_selection_version: Literal[0, 1, 2, 3, 4, 5, 6] = Field(
        default=6, exclude_if=lambda value: value == 0
    )
    analysis: AnalysisOptions = Field(default_factory=AnalysisOptions)
    node_timeout_seconds: Annotated[float, Field(gt=0, le=60, allow_inf_nan=False)] = 30.0
    max_response_bytes: Annotated[PositiveCount, Field(le=1_000_000)] = 100_000
    recursion_limit: Annotated[PositiveCount, Field(le=512)] = 64


class ResearchModel(PlanningModel, Protocol):
    async def evaluate_coverage(self, request: CoverageInput) -> object: ...
    async def synthesize(self, request: SynthesisInput) -> object: ...
    async def critique(self, request: CriticInput) -> object: ...


@runtime_checkable
class QuoteSelectionModel(Protocol):
    async def select_quotes(self, request: SynthesisInput) -> object: ...


@runtime_checkable
class QuoteCriticModel(Protocol):
    async def critique_quotes(self, request: CriticInput) -> object: ...


@runtime_checkable
class ConstrainedQuoteSelectionModel(Protocol):
    async def select_quotes_constrained(self, request: SynthesisInput) -> object: ...


@runtime_checkable
class CompactQuoteSelectionModel(Protocol):
    async def select_quotes_compact(self, request: SynthesisInput) -> object: ...
