"""Generate bounded source-specific queries after both initialization branches finish."""

import asyncio

from pydantic import ValidationError

from evidenceforge.graph.state import ResearchState, StateSnapshot, validate_state
from evidenceforge.identity import stable_id
from evidenceforge.models.base import PlanningModel
from evidenceforge.nodes.common import (
    Update,
    blocked_model_patch,
    checked_patch,
    event_patch,
    failure_patch,
    record_data,
)
from evidenceforge.planning import (
    ModelBudgetExceeded,
    ModelUnavailable,
    PlanningContractError,
    PlanningOptions,
    QueryBatchDraft,
    QueryDraft,
    QueryGenerationRequest,
    normalized,
    parse_response,
)
from evidenceforge.schemas import SearchQuery, SourceType


def query_key(text: str, source_type: SourceType, owner_scope: str) -> str:
    """Attempt identity ignores casing/spacing, pass and question grouping."""
    return stable_id("query_key", owner_scope, source_type.value, normalized(text))


class QueryGenerator:
    def __init__(self, model: PlanningModel, options: PlanningOptions) -> None:
        self.model = model
        self.options = options

    async def __call__(self, state: ResearchState) -> Update:
        state = validate_state(state)
        snapshot = StateSnapshot.model_validate(state)
        statuses = {
            result.role: result.status for result in snapshot.initialization_results.values()
        }
        if set(statuses) != {"planner", "context_manager"} or "failed" in statuses.values():
            return failure_patch(state, "query_generator", "schema")
        available_sources = tuple(
            source
            for source in self.options.available_source_types
            if source != SourceType.DOCUMENT
            or any(reference.kind == "document" for reference in snapshot.context_refs)
        )
        if not available_sources:
            return failure_patch(state, "query_generator", "provider")
        if snapshot.iteration_count >= snapshot.budget.max_research_passes:
            return failure_patch(state, "query_generator", "budget")
        # Searches are reserved/consumed by retrieval in Phase 3, not by merely drafting a query.
        used_searches = sum(
            reservation.searches
            for reservation in snapshot.reservations.values()
            if reservation.status != "released"
        )
        remaining = snapshot.budget.max_searches - used_searches
        max_queries = min(snapshot.budget.max_queries_per_pass, remaining)
        if max_queries <= 0:
            return failure_patch(state, "query_generator", "budget")
        if (
            snapshot.budget.max_model_calls - snapshot.planning_attempts - snapshot.quality_attempts
            <= snapshot.budget.reserved_quality_calls
        ):
            return failure_patch(state, "query_generator", "budget")

        def failed(category: str) -> Update:
            return checked_patch(
                state,
                {
                    **failure_patch(state, "query_generator", category),
                    "planning_attempts": snapshot.planning_attempts + 1,
                },
            )

        request = QueryGenerationRequest(
            request=snapshot.request,
            questions=snapshot.research_questions,
            context_refs=snapshot.context_refs,
            gaps=snapshot.gaps,
            attempted_query_keys=snapshot.attempted_query_keys,
            available_source_types=available_sources,
            research_pass=snapshot.iteration_count + 1,
            max_queries=max_queries,
        )
        try:
            response = await asyncio.wait_for(
                self.model.generate_queries(request),
                timeout=self.options.node_timeout_seconds,
            )
            batch = parse_response(response, QueryBatchDraft, self.options.max_response_bytes)
            if len(batch.queries) > max_queries:
                raise PlanningContractError("query allowance exceeded")
            known_questions = {question.id for question in snapshot.research_questions}
            grouped: dict[str, QueryDraft] = {}
            for draft in batch.queries:
                if not set(draft.question_ids).issubset(known_questions):
                    raise PlanningContractError("unknown query question")
                if draft.source_type not in available_sources:
                    raise PlanningContractError("source channel unavailable")
                key = query_key(draft.text, draft.source_type, snapshot.owner_scope)
                if key in snapshot.attempted_query_keys:
                    continue
                previous = grouped.get(key)
                if previous is not None:
                    if previous.purpose != draft.purpose:
                        raise PlanningContractError("duplicate queries have conflicting purposes")
                    draft = QueryDraft(
                        question_ids=tuple(
                            sorted(set(previous.question_ids) | set(draft.question_ids))
                        ),
                        text=previous.text,
                        source_type=draft.source_type,
                        purpose=draft.purpose,
                    )
                grouped[key] = draft
            queries = [
                SearchQuery(
                    id=stable_id(
                        "query",
                        snapshot.owner_scope,
                        key,
                        request.research_pass,
                        list(sorted(draft.question_ids)),
                        draft.purpose,
                    ),
                    question_ids=tuple(sorted(draft.question_ids)),
                    text=" ".join(draft.text.split()),
                    source_type=draft.source_type,
                    research_pass=request.research_pass,
                    purpose=draft.purpose,
                )
                for key, draft in grouped.items()
            ]
            return checked_patch(
                state,
                {
                    "search_queries": [record_data(query) for query in queries],
                    "query_records": {query.id: record_data(query) for query in queries},
                    "planning_status": "ready",
                    "planning_attempts": snapshot.planning_attempts + 1,
                    **event_patch(
                        state,
                        "query_generator",
                        "queries_generated",
                        f"Prepared {len(queries)} queries for the next retrieval pass.",
                    ),
                },
            )
        except (ValidationError, PlanningContractError):
            return failed("schema")
        except TimeoutError:
            return failed("timeout")
        except ModelBudgetExceeded as exc:
            return blocked_model_patch(state, "query_generator", exc.reason, failed("budget"))
        except ModelUnavailable:
            return failed("provider")
