"""Structured research inputs and validated model-output boundaries."""

from typing import Annotated, Literal, Protocol

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
    duplicate_evidence: tuple[DuplicateEvidence, ...] = ()
    questions: tuple[ResearchQuestion, ...]
    evidence: tuple[EvidenceItem, ...]


class DraftClaim(Contract):
    statement: Text
    question_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    evidence_ids: tuple[Identifier, ...] = ()
    kind: ClaimKind = ClaimKind.FACT
    qualifiers: tuple[Text, ...] = ()
    section: Literal["summary", "key_findings", "limitations", "disagreements"] = "key_findings"


class ReportDraft(Contract):
    claims: Annotated[tuple[DraftClaim, ...], Field(min_length=1, max_length=64)]


class SynthesisInput(Contract):
    duplicate_evidence: tuple[DuplicateEvidence, ...] = ()
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
    duplicate_evidence: tuple[DuplicateEvidence, ...] = ()
    report: Report
    claims: tuple[Claim, ...]
    evidence: tuple[EvidenceItem, ...]
    coverage: tuple[QuestionCoverage, ...]


class CriticAssessment(Contract):
    decision: Literal["approved", "revise"]
    revision_brief: tuple[Text, ...] = ()


class ResearchOptions(Contract):
    require_plan_approval: bool = False
    live_web: StrictBool = False
    live_energy: StrictBool = False
    analysis: AnalysisOptions = Field(default_factory=AnalysisOptions)
    node_timeout_seconds: Annotated[float, Field(gt=0, le=60, allow_inf_nan=False)] = 30.0
    max_response_bytes: Annotated[PositiveCount, Field(le=1_000_000)] = 100_000
    recursion_limit: Annotated[PositiveCount, Field(le=512)] = 64


class ResearchModel(PlanningModel, Protocol):
    async def evaluate_coverage(self, request: CoverageInput) -> object: ...
    async def synthesize(self, request: SynthesisInput) -> object: ...
    async def critique(self, request: CriticInput) -> object: ...
