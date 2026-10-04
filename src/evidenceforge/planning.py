"""Phase 2 planning contracts; IDs are assigned by nodes, never by model output."""

import json
from typing import Annotated, Self

from pydantic import BaseModel, Field, StrictBool, StringConstraints, model_validator

from evidenceforge.schemas import (
    ContextReference,
    Contract,
    Identifier,
    PositiveCount,
    Record,
    ResearchGap,
    ResearchQuestion,
    ResearchRequest,
    Score,
    SourceType,
    Text,
)


class PlanningContractError(ValueError):
    """Expected malformed/unusable planning output; never include raw output in diagnostics."""


class ModelUnavailable(RuntimeError):
    """Expected adapter failure; raw provider messages stay outside public events."""


class ContextUnavailable(RuntimeError):
    """An optional context repository cannot currently be read."""


def normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


class QuestionDraft(Contract):
    question: Annotated[Text, Field(max_length=1000)]
    acceptance_criteria: Annotated[tuple[Text, ...], Field(min_length=1, max_length=8)]
    importance: Score = 1.0

    @model_validator(mode="after")
    def one_focus(self) -> Self:
        if self.importance <= 0:
            raise ValueError("question importance must be positive")
        if "\n" in self.question or "\r" in self.question or self.question.count("?") > 1:
            raise ValueError("one focused question per record is required")
        return self


class PlanDraft(Contract):
    questions: Annotated[tuple[QuestionDraft, ...], Field(min_length=1, max_length=32)]

    @model_validator(mode="after")
    def distinct_questions(self) -> Self:
        names = [normalized(question.question) for question in self.questions]
        if len(names) != len(set(names)):
            raise ValueError("duplicate focused questions")
        return self


class QueryDraft(Contract):
    question_ids: Annotated[tuple[Identifier, ...], Field(min_length=1, max_length=32)]
    text: Annotated[Text, Field(max_length=1000)]
    source_type: SourceType
    purpose: Annotated[
        str, StringConstraints(pattern=r"^(support|counter_evidence|primary_source)$")
    ] = "support"

    @model_validator(mode="after")
    def unique_questions(self) -> Self:
        if len(self.question_ids) != len(set(self.question_ids)):
            raise ValueError("duplicate query question IDs")
        return self


class QueryBatchDraft(Contract):
    queries: Annotated[tuple[QueryDraft, ...], Field(min_length=1, max_length=64)]


class ContextBatch(Contract):
    references: Annotated[tuple[ContextReference, ...], Field(max_length=64)] = ()


class QueryGenerationRequest(Contract):
    request: ResearchRequest
    questions: tuple[ResearchQuestion, ...]
    context_refs: tuple[ContextReference, ...]
    gaps: tuple[ResearchGap, ...]
    attempted_query_keys: tuple[str, ...]
    available_source_types: tuple[SourceType, ...]
    research_pass: PositiveCount
    max_queries: PositiveCount


class PlanningOptions(Contract):
    available_source_types: tuple[SourceType, ...] = (SourceType.WEB, SourceType.DOCUMENT)
    max_context_refs: Annotated[PositiveCount, Field(le=64)] = 32
    max_response_bytes: Annotated[PositiveCount, Field(le=1_000_000)] = 100_000
    node_timeout_seconds: Annotated[float, Field(gt=0, le=60, allow_inf_nan=False)] = 30.0
    include_prior_reports: StrictBool = True

    @model_validator(mode="after")
    def source_types_unique(self) -> Self:
        if not self.available_source_types:
            raise ValueError("at least one configured source type is required")
        if len(self.available_source_types) != len(set(self.available_source_types)):
            raise ValueError("configured source types must be unique")
        return self


class InitializationResult(Record):
    role: Annotated[str, StringConstraints(pattern=r"^(planner|context_manager)$")]
    status: Annotated[str, StringConstraints(pattern=r"^(ready|unavailable|failed)$")]


def parse_response[T: Contract](payload: object, schema: type[T], max_bytes: int) -> T:
    """Validate JSON boundary and byte size without saving raw malformed model responses."""
    try:
        if isinstance(payload, BaseModel):
            payload = payload.model_dump(mode="json")
        if isinstance(payload, str):
            encoded = payload
        else:
            encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, RecursionError) as exc:
        raise PlanningContractError("response is not JSON data") from exc
    try:
        byte_count = len(encoded.encode("utf-8"))
    except UnicodeError as exc:
        raise PlanningContractError("response is not valid UTF-8") from exc
    if byte_count > max_bytes:
        raise PlanningContractError("response exceeds configured size")
    return schema.model_validate_json(encoded)
