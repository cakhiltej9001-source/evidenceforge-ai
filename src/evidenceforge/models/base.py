"""Read-only structured-output port; no tool acquisition or provider credentials in state."""

from typing import Protocol

from evidenceforge.planning import QueryGenerationRequest
from evidenceforge.schemas import ResearchRequest


class PlanningModel(Protocol):
    @property
    def is_fixture(self) -> bool: ...

    async def plan(self, request: ResearchRequest, *, max_questions: int) -> object: ...

    async def generate_queries(self, request: QueryGenerationRequest) -> object: ...
