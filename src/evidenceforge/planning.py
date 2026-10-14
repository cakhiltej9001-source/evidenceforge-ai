"""Phase 2 planning contracts; IDs are assigned by nodes, never by model output."""

import json
import re
from typing import Annotated, Literal, Self

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


class PlanScopeError(PlanningContractError):
    """A bounded scope rule rejected a model's added acceptance requirement."""


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


class ReviewedPlanDraft(Contract):
    """One structured review/plan boundary; rejected requests cannot carry a plan."""

    category: Literal["research", "gibberish", "non_research", "manipulation", "vague"]
    questions: Annotated[tuple[QuestionDraft, ...], Field(max_length=32)]

    @model_validator(mode="after")
    def reviewed_plan(self) -> Self:
        if self.category == "research":
            PlanDraft(questions=self.questions)
        elif self.questions:
            raise ValueError("rejected requests must not include a plan")
        return self


_TEMPORAL_BREAKDOWNS = {
    "hour": r"\b(?:hourly|hour[- ]by[- ]hour|(?:per|each|every|by)\s+hours?)\b",
    "day": r"\b(?:daily|day[- ]by[- ]day|(?:per|each|every|by)\s+days?)\b",
    "week": r"\b(?:weekly|week[- ]by[- ]week|(?:per|each|every|by)\s+weeks?)\b",
    "month": r"\b(?:monthly|month[- ]by[- ]month|(?:per|each|every|by)\s+months?)\b",
    "quarter": r"\b(?:quarterly|quarter[- ]by[- ]quarter|(?:per|each|every|by)\s+quarters?)\b",
}
_MONTH_NAME = (
    r"(?:january|february|march|april|may(?=\s+\d)|june|july|august|"
    r"september|october|november|december)"
)


def validate_plan_scope(request: ResearchRequest, plan: PlanDraft) -> None:
    """Reject added subannual requirements in an explicitly year-scoped request.

    This is a narrow deterministic safeguard for the observed annual-to-monthly
    drift, not a semantic judgment of every possible research scope. Explicitly
    requested breakdowns remain allowed; nothing is silently removed or rewritten.
    """
    requested = normalized(" ".join((request.question, *request.preferences)))
    if not re.search(r"\b(?:19\d{2}|20\d{2}|annual|annually|yearly)\b", requested):
        return
    allowed = {
        unit for unit, pattern in _TEMPORAL_BREAKDOWNS.items() if re.search(pattern, requested)
    }
    # Month/date and seasonal context permit monthly supporting measurements,
    # not every possible finer breakdown. Bare chronology nouns are not criteria.
    if re.search(
        rf"\b(?:\d{{4}}-\d{{2}}(?:-\d{{2}})?|{_MONTH_NAME}|seasonal|seasonally|seasons)\b",
        requested,
    ):
        allowed.add("month")
    if re.search(r"\b\d{4}-\d{2}-\d{2}\b", requested) or re.search(
        rf"\b(?:{_MONTH_NAME}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s*,\s*|\s+)\d{{4}}|"
        rf"\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH_NAME}\s+\d{{4}})\b",
        requested,
    ):
        allowed.add("day")
    proposed = " ".join(
        text
        for question in plan.questions
        for text in (question.question, *question.acceptance_criteria)
    ).casefold()
    if any(
        re.search(pattern, proposed) and unit not in allowed
        for unit, pattern in _TEMPORAL_BREAKDOWNS.items()
    ):
        raise PlanScopeError("unrequested temporal breakdown")


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
