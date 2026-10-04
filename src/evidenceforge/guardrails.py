"""Deterministic request checks before planning, retrieval or paid model work."""

from pydantic import ValidationError

from evidenceforge.config import ConfigurationError
from evidenceforge.schemas import InputDecision, InputStatus, ResearchRequest

_VAGUE = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "help",
        "do research",
        "research this",
        "tell me something",
        "answer this",
    }
)


class InputReviewRequired(ConfigurationError):
    """Expose a bounded decision, never raw input or validation details."""

    def __init__(self, decision: InputDecision) -> None:
        self.decision = decision
        super().__init__(f"{decision.status.value}: {decision.reason}")


def _review(value: object) -> tuple[InputDecision, ResearchRequest | None]:
    try:
        request = ResearchRequest.model_validate(value)
    except ValidationError:
        return InputDecision(
            status=InputStatus.REJECTED,
            reason="Invalid research request. Supply a nonblank bounded question and valid scope.",
        ), None
    focus = " ".join(request.question.casefold().split()).strip(" .!?")
    if focus in _VAGUE or not any(character.isalnum() for character in focus):
        return InputDecision(
            status=InputStatus.NEEDS_CLARIFICATION,
            reason="Provide a research topic and what you want to investigate or compare.",
        ), request
    return InputDecision(
        status=InputStatus.ACCEPTED,
        reason="Basic input checks passed; factual answerability is unverified.",
    ), request


def assess_input(value: object) -> InputDecision:
    """A small explicit policy, not a semantic safety or answerability classifier."""
    return _review(value)[0]


def require_research_request(value: object) -> ResearchRequest:
    decision, request = _review(value)
    if decision.status != InputStatus.ACCEPTED or request is None:
        raise InputReviewRequired(decision) from None
    return request
