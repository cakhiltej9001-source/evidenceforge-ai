"""Offline regression for added temporal criteria in a year-scoped question."""

import asyncio

import pytest

from evidenceforge.graph.state import apply_update, initial_state
from evidenceforge.models.fixtures import FixturePlanningModel
from evidenceforge.nodes.planner import Planner
from evidenceforge.planning import PlanDraft, PlanningOptions, PlanScopeError, validate_plan_scope
from evidenceforge.schemas import ResearchRequest, ToolError
from evidenceforge.services.planning import PlanningService

QUESTION = "Investigate disagreement in Northfield solar electricity output for 2024."


def plan(criteria, question=QUESTION):
    return {"questions": [{"question": question, "acceptance_criteria": criteria}]}


@pytest.mark.parametrize(
    "added",
    [
        "Monthly totals and variance",
        "Daily output",
        "Hourly measurements",
        "Quarterly totals",
        "Week-by-week output",
    ],
)
def test_year_scoped_request_rejects_unrequested_breakdowns(added):
    draft = PlanDraft.model_validate(plan(["Comparable 2024 output", added]))
    with pytest.raises(PlanScopeError, match="unrequested temporal breakdown"):
        validate_plan_scope(ResearchRequest(question=QUESTION), draft)


def test_breakdown_in_subquestion_is_also_rejected():
    draft = PlanDraft.model_validate(plan(["Primary output"], "What was monthly output in 2024?"))
    with pytest.raises(PlanScopeError):
        validate_plan_scope(ResearchRequest(question=QUESTION), draft)


def test_monthly_drift_stops_before_queries_and_explains_recovery():
    model = FixturePlanningModel(
        plan_output=plan(["Comparable annual 2024 measurements", "Monthly totals and variance"])
    )
    state = asyncio.run(PlanningService(model).plan(ResearchRequest(question=QUESTION)))
    assert state["planning_status"] == state["run_status"] == "failed"
    assert state["research_questions"] == state["search_queries"] == []
    assert model.plan_calls == 1 and model.query_calls == 0
    messages = [error["message"] for error in state["tool_errors"].values()]
    assert any("unrequested temporal breakdown" in message for message in messages)
    assert any("create a new plan" in message for message in messages)
    assert "plan_scope_rejected" in {event["kind"] for event in state["events"].values()}


def test_annual_disagreement_plan_remains_usable():
    model = FixturePlanningModel(
        plan_output=plan(["Compare 2024 output under the same population and conditions"])
    )
    state = asyncio.run(PlanningService(model).plan(ResearchRequest(question=QUESTION)))
    assert state["planning_status"] == "ready"
    assert model.plan_calls == model.query_calls == 1


@pytest.mark.parametrize(
    "question",
    [
        "Compare monthly Northfield solar output in 2024.",
        "Compare month-by-month Northfield solar output in 2024.",
        "How did seasonal Northfield solar output change in 2024?",
        "What was Northfield solar output in January 2024?",
        "What was Northfield solar output on 2024-01-01?",
    ],
)
def test_requested_breakdown_is_preserved(question):
    draft = PlanDraft.model_validate(plan(["Monthly output"]))
    validate_plan_scope(ResearchRequest(question=question), draft)


def test_modal_may_does_not_hide_annual_scope_drift():
    draft = PlanDraft.model_validate(plan(["Monthly output"]))
    with pytest.raises(PlanScopeError):
        validate_plan_scope(
            ResearchRequest(question="What may explain solar output disagreement in 2024?"),
            draft,
        )


def test_requested_monthly_scope_does_not_authorize_new_daily_requirements():
    draft = PlanDraft.model_validate(plan(["Daily output"]))
    with pytest.raises(PlanScopeError):
        validate_plan_scope(
            ResearchRequest(question="Compare monthly Northfield solar output in 2024."),
            draft,
        )


def test_scope_rejection_preserves_existing_immutable_errors():
    previous = ToolError(
        id="error_previous",
        provider="context_manager",
        category="provider",
        retryable=False,
        attempt=1,
        message="The configured adapter is unavailable.",
    ).model_dump(mode="json")
    state = apply_update(
        initial_state(ResearchRequest(question=QUESTION)),
        {"tool_errors": {"error_previous": previous}},
    )
    model = FixturePlanningModel(plan_output=plan(["Monthly output"]))
    update = asyncio.run(Planner(model, PlanningOptions())(state))
    result = apply_update(state, update)
    assert result["tool_errors"]["error_previous"] == previous
    assert state["tool_errors"]["error_previous"] == previous
    assert any(
        "unrequested temporal breakdown" in error["message"]
        for error in result["tool_errors"].values()
    )


@pytest.mark.parametrize("unit", ["gigawatt-hours", "gigawatt hours", "kilowatt hours"])
def test_energy_units_are_not_temporal_breakdowns(unit):
    draft = PlanDraft.model_validate(plan([f"Comparable annual output in {unit}"]))
    validate_plan_scope(ResearchRequest(question=QUESTION), draft)


def test_explicit_breakdown_preference_is_preserved():
    draft = PlanDraft.model_validate(plan(["Monthly output"]))
    validate_plan_scope(
        ResearchRequest(question=QUESTION, preferences=("Provide monthly totals.",)), draft
    )


@pytest.mark.parametrize("added", ["Break down by hour", "Output each hour", "Per hour output"])
def test_explicit_hourly_phrases_are_still_rejected(added):
    draft = PlanDraft.model_validate(plan([added]))
    with pytest.raises(PlanScopeError):
        validate_plan_scope(ResearchRequest(question=QUESTION), draft)
