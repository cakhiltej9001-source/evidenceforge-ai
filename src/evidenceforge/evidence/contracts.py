"""Versioned ranking, scoped numeric propositions, and graph export contracts."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from evidenceforge.schemas import Contract, Count, Identifier, PositiveCount, Record, Score, Text

Unit = Literal["Wh", "kWh", "MWh", "GWh", "TWh", "W", "kW", "MW", "GW", "%"]
RankingProfile = Literal["general", "current", "historical"]
ComparisonRelationship = Literal["supports", "contradicts", "not_comparable", "duplicate"]


class AnalysisOptions(Contract):
    ranking_profile: Literal["general", "current", "historical"] = "general"
    max_propositions: Annotated[PositiveCount, Field(le=256)] = 128
    max_comparisons: Annotated[PositiveCount, Field(le=10000)] = 2000


class RankingFeature(Contract):
    name: Identifier
    value: Score | None
    weight: Score
    rationale: Text


class SourceQuality(Contract):
    source_id: Identifier
    version: Literal["weighted_metadata_v1"] = "weighted_metadata_v1"
    profile: Literal["general", "current", "historical"]
    score: Score
    observed_weight: Score
    family_group: Identifier
    family_size: PositiveCount
    features: tuple[RankingFeature, ...]

    @model_validator(mode="after")
    def check_features(self) -> Self:
        if len({f.name for f in self.features}) != len(self.features):
            raise ValueError("ranking features must be unique")
        if abs(sum(f.weight for f in self.features) - 1.0) > 1e-8:
            raise ValueError("ranking weights must sum to one")
        expected = sum(f.weight * (0.5 if f.value is None else f.value) for f in self.features)
        known = sum(f.weight for f in self.features if f.value is not None)
        if abs(self.score - expected) > 1e-8 or abs(self.observed_weight - known) > 1e-8:
            raise ValueError("ranking score/known weight differs from its features")
        return self


class Proposition(Record):
    evidence_id: Identifier
    question_ids: tuple[Identifier, ...]
    start_offset: Count
    end_offset: PositiveCount
    quote: Text
    entity: Text
    metric: Text
    timeframe: Text
    population: Text
    conditions: Text
    value: Annotated[Decimal, Field(max_digits=24, decimal_places=9, allow_inf_nan=False)]
    unit: Unit
    extractor: Literal["scoped_numeric_v1"] = "scoped_numeric_v1"

    @model_validator(mode="after")
    def span(self) -> Self:
        if self.end_offset - self.start_offset != len(self.quote):
            raise ValueError("proposition quote length differs from its span")
        if not self.question_ids or len(set(self.question_ids)) != len(self.question_ids):
            raise ValueError("proposition requires unique question IDs")
        return self


class Comparison(Record):
    left_id: Identifier
    right_id: Identifier
    question_ids: tuple[Identifier, ...]
    relationship: Literal["supports", "contradicts", "not_comparable", "duplicate"]
    rationale: Text
    normalized_left: Text | None = None
    normalized_right: Text | None = None
    canonical_unit: Text | None = None
    version: Literal["scoped_numeric_v1"] = "scoped_numeric_v1"

    @model_validator(mode="after")
    def pair(self) -> Self:
        if self.left_id >= self.right_id or not self.question_ids:
            raise ValueError("comparison needs distinct ordered propositions and questions")
        return self


class GraphNode(Contract):
    id: Identifier
    kind: Literal["question", "claim", "evidence", "source"]
    label: str
    record: dict[str, object]


class GraphEdge(Contract):
    id: Identifier
    source: Identifier
    target: Identifier
    relationship: Literal[
        "addresses",
        "supports",
        "contradicts",
        "contextualizes",
        "uncertain",
        "retrieved_from",
        "duplicate_of",
    ]
    rationale: Text
    record_id: Identifier | None = None


class EvidenceGraph(Contract):
    version: Literal["evidence_graph_v1"] = "evidence_graph_v1"
    run_id: Identifier
    owner_scope: Identifier
    draft_version: Count
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    gap_records: tuple[dict[str, object], ...]

    @model_validator(mode="after")
    def references(self) -> Self:
        ids = {n.id for n in self.nodes}
        if len(ids) != len(self.nodes) or len({e.id for e in self.edges}) != len(self.edges):
            raise ValueError("graph IDs must be unique")
        if any(e.source not in ids or e.target not in ids for e in self.edges):
            raise ValueError("graph edge has an unknown endpoint")
        return self
