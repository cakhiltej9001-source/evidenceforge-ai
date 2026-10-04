"""Query normalization, source availability, pass and search allowance checks."""

import asyncio
import json
from copy import deepcopy

import pytest

from evidenceforge.graph.state import apply_update
from evidenceforge.models.fixtures import FixturePlanningModel
from evidenceforge.nodes.queries import QueryGenerator, query_key
from evidenceforge.planning import ModelUnavailable, PlanningOptions
from evidenceforge.schemas import (
    BudgetLimits,
    BudgetReservation,
    CallRecord,
    ResearchRequest,
    SourceType,
)
from evidenceforge.services.planning import PlanningService

REQUEST = ResearchRequest(question="Compare solar and wind electricity generation.")


def prepared(budget=None):
    return asyncio.run(PlanningService().plan(REQUEST, budget))


def query(
    state, text="solar primary measurements", source="web", question_ids=None, purpose="support"
):
    return {
        "question_ids": question_ids or [state["research_questions"][0]["id"]],
        "text": text,
        "source_type": source,
        "purpose": purpose,
    }


def generate(state, output, options=None):
    model = FixturePlanningModel(query_output=output)
    before = deepcopy(state)
    patch = asyncio.run(QueryGenerator(model, options or PlanningOptions())(state))
    assert state == before
    return apply_update(state, patch), model


def test_duplicate_normalized_queries_merge_question_associations():
    state = prepared()
    q1, q2 = [q["id"] for q in state["research_questions"][:2]]
    result, model = generate(
        state,
        {
            "queries": [
                query(state, " Solar   measurements ", question_ids=[q1]),
                query(state, "solar measurements", question_ids=[q2]),
            ]
        },
    )
    assert model.query_calls == 1 and len(result["search_queries"]) == 1
    assert result["search_queries"][0]["question_ids"] == sorted([q1, q2])
    assert result["search_queries"][0]["text"] == "Solar measurements"
    assert not result["attempted_query_keys"]
    again, _ = generate(
        state,
        {
            "queries": [
                query(
                    state,
                    "solar measurements",
                    question_ids=[q2, q1],
                )
            ]
        },
    )
    assert result["search_queries"][0]["id"] == again["search_queries"][0]["id"]


def test_attempted_query_keys_are_source_and_owner_scoped():
    text = "Solar Measurements"
    assert query_key(text, SourceType.WEB, "local") == query_key(
        " solar   measurements ", SourceType.WEB, "local"
    )
    assert query_key(text, SourceType.WEB, "local") != query_key(text, SourceType.DOCUMENT, "local")
    assert query_key(text, SourceType.WEB, "local") != query_key(text, SourceType.WEB, "other")
    state = apply_update(
        prepared(),
        {
            "attempted_query_keys": [query_key(text, SourceType.WEB, "local")],
        },
    )
    result, _ = generate(
        state,
        {
            "queries": [
                query(state, "solar measurements"),
                query(state, "wind measurements"),
            ]
        },
    )
    assert [q["text"] for q in result["search_queries"]] == ["wind measurements"]
    empty, _ = generate(state, {"queries": [query(state, text)]})
    assert empty["planning_status"] == "ready" and empty["search_queries"] == []


@pytest.mark.parametrize(
    "kind",
    [
        "unknown_question",
        "document_unavailable",
        "api_unavailable",
        "too_many",
        "bad_purpose",
        "missing_source",
        "duplicate_question",
        "conflicting_purpose",
        "extra_field",
    ],
)
def test_invalid_queries_are_typed_failures_and_not_added_to_history(kind):
    state = prepared()
    item = query(state)
    queries = [item]
    if kind == "unknown_question":
        item["question_ids"] = ["unknown_question"]
    elif kind == "document_unavailable":
        item["source_type"] = "document"
    elif kind == "api_unavailable":
        item["source_type"] = "api"
    elif kind == "too_many":
        queries = [query(state, f"measurement {i}") for i in range(5)]
    elif kind == "bad_purpose":
        item["purpose"] = "unsupported_instruction"
    elif kind == "missing_source":
        del item["source_type"]
    elif kind == "duplicate_question":
        item["question_ids"] *= 2
    elif kind == "conflicting_purpose":
        queries.append(query(state, purpose="counter_evidence"))
    elif kind == "extra_field":
        item["secret"] = "sensitive_output"
    result, model = generate(state, {"queries": queries})
    assert result["planning_status"] == result["run_status"] == "failed"
    assert result["query_records"] == state["query_records"]
    assert model.query_calls == 1
    assert {e["category"] for e in result["tool_errors"].values()} == {"schema"}
    assert "sensitive_output" not in json.dumps(result)


def test_pass_uses_completed_batches_plus_one_and_is_bounded():
    state = apply_update(prepared(), {"iteration_count": 1})
    result, _ = generate(state, {"queries": [query(state)]})
    assert result["search_queries"][0]["research_pass"] == 2
    assert result["iteration_count"] == 1
    exhausted = apply_update(prepared(), {"iteration_count": 3})
    result, model = generate(exhausted, {"queries": [query(exhausted)]})
    assert result["planning_status"] == "failed"
    assert model.query_calls == 0
    assert {e["category"] for e in result["tool_errors"].values()} == {"budget"}


@pytest.mark.parametrize(
    "status,searches,expected",
    [
        ("reserved", 11, 1),
        ("settled", 11, 1),
        ("released", 12, 3),
        ("reserved", 12, 0),
    ],
)
def test_query_allowance_accounts_for_reserved_or_settled_searches(status, searches, expected):
    state = prepared()
    call = CallRecord(
        id="call_a",
        request_hash="a" * 64,
        provider="fixture",
        kind="search",
        status="pending",
        started_at=state["started_at"],
    )
    reservation = BudgetReservation(
        id="reservation_a", call_id=call.id, searches=searches, status=status
    )
    state = apply_update(
        state,
        {
            "calls": {call.id: call.model_dump(mode="json")},
            "reservations": {reservation.id: reservation.model_dump(mode="json")},
        },
    )
    model = FixturePlanningModel()
    patch = asyncio.run(QueryGenerator(model, PlanningOptions())(state))
    result = apply_update(state, patch)
    if expected:
        assert result["planning_status"] == "ready"
        assert len(result["search_queries"]) == expected
        assert model.query_calls == 1
    else:
        assert result["planning_status"] == "failed"
        assert model.query_calls == 0
    assert result["reservations"] == state["reservations"]


@pytest.mark.parametrize("kind", ["timeout", "unavailable"])
def test_query_adapter_failure_has_no_raw_provider_details(kind):
    class Model(FixturePlanningModel):
        async def generate_queries(self, request):
            if kind == "unavailable":
                raise ModelUnavailable("secret-provider-detail")
            await asyncio.Event().wait()

    state = prepared()
    patch = asyncio.run(
        QueryGenerator(
            Model(),
            PlanningOptions(node_timeout_seconds=0.02),
        )(state)
    )
    result = apply_update(state, patch)
    assert result["planning_status"] == "failed"
    assert "secret-provider-detail" not in json.dumps(result)
    assert {e["category"] for e in result["tool_errors"].values()} == {
        "timeout" if kind == "timeout" else "provider"
    }


def test_query_generator_does_not_run_model_before_both_branches():
    from evidenceforge.graph.state import initial_state

    state = initial_state(REQUEST)
    result, model = generate(state, {"queries": []})
    assert model.query_calls == 0
    assert result["planning_status"] == "failed"


def test_configured_api_query_is_metadata_only_and_makes_no_external_calls():
    model = FixturePlanningModel()
    state = asyncio.run(
        PlanningService(
            model,
            options=PlanningOptions(available_source_types=("api",)),
        ).plan(REQUEST, BudgetLimits(max_queries_per_pass=1))
    )
    assert state["planning_status"] == "ready"
    assert [q["source_type"] for q in state["search_queries"]] == ["api"]
    assert not state["calls"] and not state["source_records"]
