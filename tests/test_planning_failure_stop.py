"""An upstream provider failure cannot become a downstream query-schema error."""

import asyncio

from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.planning import ModelUnavailable
from evidenceforge.research import ResearchOptions
from evidenceforge.schemas import BudgetLimits, ResearchRequest
from evidenceforge.services.research import ResearchService


def test_planning_provider_failure_stops_before_query_preparation(tmp_path):
    requests = []

    class UnavailablePlanner(FixtureResearchModel):
        async def plan(self, request, *, max_questions):
            requests.append(request)
            raise ModelUnavailable("Synthetic provider timeout")

    budget = BudgetLimits(max_model_calls=6, max_searches=1)
    service = ResearchService(
        tmp_path,
        model=UnavailablePlanner(),
        options=ResearchOptions(production_policy_version=6, require_plan_approval=True),
    )
    state = asyncio.run(
        service.run(ResearchRequest(question="How to become an AI engineer?"), budget)
    )
    assert len(requests) == 1
    assert state["run_status"] == "failed"
    assert state["planning_attempts"] == 1
    assert not state["search_queries"] and not state["reservations"]
    assert len(state["tool_errors"]) == 1
    error = next(iter(state["tool_errors"].values()))
    assert error["provider"] == "planner" and error["category"] == "provider"
