"""Fixture-first planning service; fresh run and complete snapshot validation."""

from evidenceforge.graph.builder import build_planning_graph
from evidenceforge.graph.state import ResearchState, initial_state, validate_state
from evidenceforge.guardrails import require_research_request
from evidenceforge.models.base import PlanningModel
from evidenceforge.models.fixtures import FixturePlanningModel
from evidenceforge.planning import PlanningOptions
from evidenceforge.schemas import BudgetLimits, ResearchRequest
from evidenceforge.storage.context import ContextRepository, InMemoryContextRepository


class PlanningService:
    def __init__(
        self,
        model: PlanningModel | None = None,
        repository: ContextRepository | None = None,
        options: PlanningOptions | None = None,
    ) -> None:
        self.graph = build_planning_graph(
            model if model is not None else FixturePlanningModel(),
            repository if repository is not None else InMemoryContextRepository(),
            options,
        )

    async def plan(
        self,
        request: ResearchRequest,
        budget: BudgetLimits | None = None,
    ) -> ResearchState:
        request = require_research_request(request)
        state = initial_state(request, budget)
        result = await self.graph.ainvoke(
            state,
            config={
                "max_concurrency": (budget or BudgetLimits()).max_concurrency,
                "recursion_limit": 12,
            },
        )
        return validate_state(result)
