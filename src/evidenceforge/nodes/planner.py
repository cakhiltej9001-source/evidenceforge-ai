"""Validate a model plan, then assign deterministic question identities."""

import asyncio
from typing import cast

from pydantic import ValidationError

from evidenceforge.graph.state import ResearchState, StateSnapshot, validate_state
from evidenceforge.identity import stable_id
from evidenceforge.models.base import PlanningModel
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.nodes.common import (
    Update,
    blocked_model_patch,
    checked_patch,
    event_patch,
    failure_patch,
    initialization_patch,
    record_data,
)
from evidenceforge.nodes.input_review import GUIDANCE
from evidenceforge.planning import (
    ModelBudgetExceeded,
    ModelUnavailable,
    PlanDraft,
    PlanningContractError,
    PlanningOptions,
    PlanScopeError,
    ReviewedPlanDraft,
    normalized,
    parse_response,
    validate_plan_scope,
)
from evidenceforge.schemas import ResearchQuestion, ToolError, utc_now


class Planner:
    def __init__(
        self, model: PlanningModel, options: PlanningOptions, *, reviewed_plan: bool = False
    ) -> None:
        self.model = model
        self.options = options
        self.reviewed_plan = reviewed_plan

    async def __call__(self, state: ResearchState) -> Update:
        state = validate_state(state)
        snapshot = StateSnapshot.model_validate(state)
        if (
            snapshot.budget.max_model_calls - snapshot.planning_attempts - snapshot.quality_attempts
            <= snapshot.budget.reserved_quality_calls
        ):
            return failure_patch(state, "planner", "budget")

        def failed(category: str) -> Update:
            return checked_patch(
                state,
                {
                    **failure_patch(state, "planner", category),
                    "planning_attempts": snapshot.planning_attempts + 1,
                },
            )

        try:
            review_patch: Update = {}
            if self.reviewed_plan and isinstance(self.model, GeminiResearchModel):
                response = await asyncio.wait_for(
                    self.model.review_and_plan(
                        snapshot.request, max_questions=snapshot.budget.max_subquestions
                    ),
                    timeout=self.options.node_timeout_seconds,
                )
                reviewed = parse_response(
                    response, ReviewedPlanDraft, self.options.max_response_bytes
                )
                review_patch = event_patch(
                    state,
                    "input_guardrail",
                    "input_review_" + reviewed.category,
                    GUIDANCE[reviewed.category],
                )
                if reviewed.category != "research":
                    return checked_patch(
                        state,
                        {
                            **review_patch,
                            **initialization_patch(state, "planner", "failed"),
                            "planning_attempts": snapshot.planning_attempts + 1,
                            "run_status": "failed",
                            "planning_status": "failed",
                            "stop_reason": "input_rejected",
                            "finished_at": utc_now().isoformat(),
                        },
                    )
                response = PlanDraft(questions=reviewed.questions)
            else:
                response = await asyncio.wait_for(
                    self.model.plan(
                        snapshot.request, max_questions=snapshot.budget.max_subquestions
                    ),
                    timeout=self.options.node_timeout_seconds,
                )
            plan = parse_response(response, PlanDraft, self.options.max_response_bytes)
            if len(plan.questions) > snapshot.budget.max_subquestions:
                raise PlanningContractError("subquestion allowance exceeded")
            validate_plan_scope(snapshot.request, plan)
            questions = [
                ResearchQuestion(
                    id=stable_id(
                        "question",
                        snapshot.owner_scope,
                        normalized(snapshot.request.question),
                        normalized(question.question),
                    ),
                    question=question.question,
                    acceptance_criteria=question.acceptance_criteria,
                    importance=question.importance,
                )
                for question in plan.questions
            ]
            plan_event = event_patch(
                state,
                "planner",
                "plan_created",
                f"Structured plan validated with {len(questions)} focused questions.",
            )
            return checked_patch(
                state,
                {
                    **review_patch,
                    "research_questions": [record_data(question) for question in questions],
                    "plan_version": snapshot.plan_version + 1,
                    "planning_attempts": snapshot.planning_attempts + 1,
                    **initialization_patch(state, "planner", "ready"),
                    "events": {
                        **cast(dict[str, object], review_patch.get("events", {})),
                        **cast(dict[str, object], plan_event["events"]),
                    },
                },
            )
        except PlanScopeError:
            patch = failed("schema")
            message = (
                "Plan added an unrequested temporal breakdown. "
                "Revise the research question if that breakdown is intended, "
                "then create a new plan."
            )
            # Error records are immutable. Add a dedicated scope error without
            # rewriting prior errors that checked_patch merged into this update.
            error_id = stable_id("error", snapshot.run_id, "planner", "scope")
            patch["tool_errors"] = {
                error_id: state["tool_errors"].get(error_id)
                or record_data(
                    ToolError(
                        id=error_id,
                        provider="planner",
                        category="schema",
                        retryable=False,
                        attempt=1,
                        message=message,
                    )
                )
            }
            return checked_patch(
                state,
                {**patch, **event_patch(state, "planner", "plan_scope_rejected", message)},
            )
        except (ValidationError, PlanningContractError):
            return failed("schema")
        except TimeoutError:
            return failed("timeout")
        except ModelBudgetExceeded as exc:
            return blocked_model_patch(state, "planner", exc.reason, failed("budget"))
        except ModelUnavailable:
            return failed("provider")
