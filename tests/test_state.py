import json
from copy import deepcopy

import pytest
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Overwrite
from pydantic import ValidationError

from evidenceforge.graph.reducers import (
    merge_calls,
    merge_evidence,
    merge_log,
    merge_records,
    merge_reservations,
)
from evidenceforge.graph.state import ResearchState, apply_update, initial_state, validate_state
from evidenceforge.schemas import ResearchRequest, RunEvent


def test_immutable_merge_idempotent_order_independent_and_nonmutating():
    left, right = {"a": {"id": "a", "value": 1}}, {"b": {"id": "b", "value": 2}}
    saved = deepcopy(left)
    merged = merge_records(left, right)
    assert merge_records(right, left) == merged
    assert merge_records(merged, merged) == merged
    merged["a"]["value"] = 99
    assert left == saved
    with pytest.raises(ValueError, match="conflicting"):
        merge_records(left, {"a": {"id": "a", "value": 9}})
    with pytest.raises(ValueError, match="key"):
        merge_records({}, {"wrong": {"id": "a"}})


def test_evidence_duplicates_preserve_all_provenance(populated_state):
    original = deepcopy(populated_state["evidence_store"])
    additional = deepcopy(original)
    additional["evidence_1"]["acquisition_ids"] = ["acquisition_2"]
    additional["evidence_1"]["question_ids"] = ["q_2"]
    result = merge_evidence(original, additional)
    assert result["evidence_1"]["acquisition_ids"] == ["acquisition_1", "acquisition_2"]
    assert result["evidence_1"]["question_ids"] == ["q_1", "q_2"]
    assert original == populated_state["evidence_store"]
    additional["evidence_1"]["passage"] = "A different proposition"
    with pytest.raises(ValueError, match="payload"):
        merge_evidence(original, additional)


def test_empty_merged_updates_do_not_clear_and_explicit_logs_reset(populated_state):
    event = RunEvent(id="event_1", kind="fixture", message="Safe public event")
    state = apply_update(populated_state, {"events": {event.id: event.model_dump(mode="json")}})
    assert apply_update(state, {"events": {}})["events"] == state["events"]
    cleared = apply_update(state, {"events": Overwrite({}), "search_queries": []})
    assert cleared["events"] == {}
    assert cleared["search_queries"] == []
    assert cleared["query_records"] == state["query_records"]
    with pytest.raises(ValueError, match="reset"):
        apply_update(state, {"usage": Overwrite({})})


def test_checkpoint_logs_have_explicit_limits():
    entries = {f"event_{i}": {"id": f"event_{i}"} for i in range(200)}
    with pytest.raises(ValueError, match="limit"):
        merge_log(entries, {"event_extra": {"id": "event_extra"}})


def test_calls_replay_and_advance_without_changing_identity():
    pending = {
        "id": "call_1",
        "request_hash": "a" * 64,
        "provider": "fixture",
        "kind": "model",
        "started_at": "2026-09-30T00:00:00Z",
        "status": "pending",
        "revision": 1,
    }
    completed = {
        **pending,
        "status": "completed",
        "revision": 2,
        "finished_at": "2026-09-30T00:00:01Z",
        "response_artifact_id": "snapshot_1",
    }
    result = merge_calls({"call_1": pending}, {"call_1": completed})
    assert merge_calls(result, {"call_1": pending}) == result
    assert merge_calls(result, result) == result
    with pytest.raises(ValueError, match="lifecycle"):
        merge_calls(result, {"call_1": {**pending, "revision": 3}})
    with pytest.raises(ValueError, match="identity"):
        merge_calls(result, {"call_1": {**completed, "request_hash": "b" * 64, "revision": 3}})


def test_reservation_settlement_and_replay_do_not_restore_capacity():
    reserved = {
        "id": "reservation_1",
        "call_id": "call_1",
        "status": "reserved",
        "searches": 0,
        "model_calls": 1,
        "tokens": 100,
        "estimated_cost_usd": None,
    }
    settled = {**reserved, "status": "settled"}
    result = merge_reservations({"reservation_1": reserved}, {"reservation_1": settled})
    assert merge_reservations(result, {"reservation_1": reserved}) == result
    with pytest.raises(ValueError, match="settlement"):
        merge_reservations(result, {"reservation_1": {**reserved, "status": "released"}})


def test_whole_state_json_and_actual_checkpoint_serializer_round_trip(populated_state):
    assert validate_state(json.loads(json.dumps(populated_state))) == populated_state
    serializer = JsonPlusSerializer()
    assert validate_state(serializer.loads_typed(serializer.dumps_typed(populated_state))) == (
        populated_state
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"owner_scope": "another_owner"},
        {"iteration_count": 4},
        {"revision_count": 3},
        {"coverage_status": "sufficient"},
        {"api_key": "synthetic-secret"},
        {"run_status": "completed"},
    ],
)
def test_invalid_state_is_not_admitted(populated_state, changes):
    with pytest.raises(ValidationError):
        validate_state({**populated_state, **changes})


def test_scope_dangling_references_and_content_versions_rejected(populated_state):
    candidates = []
    for field, record_id, key, value in [
        ("evidence_store", "evidence_1", "owner_scope", "another_owner"),
        ("evidence_store", "evidence_1", "source_id", "source_missing"),
        ("source_acquisitions", "acquisition_1", "snapshot_id", "snapshot_missing"),
        ("source_records", "source_1", "content_hash", "b" * 64),
    ]:
        candidate = deepcopy(populated_state)
        candidate[field][record_id][key] = value
        candidates.append(candidate)
    for candidate in candidates:
        with pytest.raises(ValidationError):
            validate_state(candidate)


def test_unknown_updates_immutable_fields_and_counter_regression_rejected(populated_state):
    for patch in ({"client": object()}, {"run_id": "other_run"}, {"plan_version": 0}):
        with pytest.raises(ValueError):
            apply_update(populated_state, patch)


def test_new_run_does_not_inherit_old_state_or_share_mutable_containers(populated_state):
    first = initial_state(ResearchRequest(question="A fresh question"))
    second = initial_state(ResearchRequest(question="A fresh question"))
    assert first["run_id"] != populated_state["run_id"]
    assert first["thread_id"] != second["thread_id"]
    assert first["evidence_store"] == {}
    assert first["citation_audit"] == []
    assert first["iteration_count"] == 0
    first["events"]["event_1"] = {"id": "event_1"}
    assert second["events"] == {}


def test_usage_is_unique_by_call_not_only_record_id(populated_state):
    candidate = deepcopy(populated_state)
    candidate["calls"] = {
        "call_1": {
            "id": "call_1",
            "request_hash": "a" * 64,
            "provider": "fixture",
            "kind": "model",
            "status": "pending",
            "revision": 1,
            "started_at": "2026-09-30T00:00:00Z",
        }
    }
    usage = {
        "id": "usage_1",
        "call_id": "call_1",
        "provider": "fixture",
        "latency_ms": 1,
    }
    candidate["usage"] = {"usage_1": usage, "usage_2": {**usage, "id": "usage_2"}}
    with pytest.raises(ValidationError, match="unique by call"):
        validate_state(candidate)


def draft_patch():
    return {
        "report_claims": {
            "claim_1": {
                "id": "claim_1",
                "statement": "Synthetic evidence contains café.",
                "kind": "fact",
                "question_ids": ["q_1"],
                "evidence_ids": ["evidence_1"],
            }
        },
        "draft_report": {
            "id": "report_1",
            "draft_version": 1,
            "sections": [
                {"name": "summary", "claim_ids": ["claim_1"]},
                {"name": "key_findings", "claim_ids": ["claim_1"]},
            ],
            "source_ids": ["source_1"],
        },
    }


def test_draft_claim_placement_and_stale_audit_checked(populated_state):
    drafted = apply_update(populated_state, draft_patch())
    with pytest.raises(ValidationError, match="place exactly"):
        apply_update(drafted, {"report_claims": {}})
    with pytest.raises(ValidationError, match="stale"):
        apply_update(
            drafted,
            {
                "citation_audit": [
                    {
                        "id": "audit_1",
                        "claim_id": "claim_1",
                        "draft_version": 2,
                        "evidence_ids": ["evidence_1"],
                        "structural_valid": True,
                        "support": "supported",
                        "rationale": "Fixture support",
                    }
                ]
            },
        )


def test_supported_completion_requires_entire_quality_contract(populated_state):
    drafted = apply_update(populated_state, draft_patch())
    common = {
        "coverage_status": "sufficient",
        "coverage_by_question": {
            "q_1": {
                "question_id": "q_1",
                "status": "sufficient",
                "evidence_ids": ["evidence_1"],
                "rationale": "Fixture support",
            }
        },
        "run_status": "completed",
        "stop_reason": "sufficient",
        "finished_at": "2099-01-01T00:00:00Z",
        "final_report": drafted["draft_report"],
        "critic_verdict": {"draft_version": 1, "decision": "approved"},
    }
    with pytest.raises(ValidationError, match="all factual claims"):
        apply_update(drafted, common)
    complete = apply_update(
        drafted,
        {
            **common,
            "citation_audit": [
                {
                    "id": "audit_1",
                    "claim_id": "claim_1",
                    "draft_version": 1,
                    "evidence_ids": ["evidence_1"],
                    "structural_valid": True,
                    "support": "supported",
                    "rationale": "Fixture-only support judgment",
                }
            ],
        },
    )
    assert complete["run_status"] == "completed"
    with pytest.raises(ValueError, match="terminal"):
        apply_update(complete, {"run_status": "running", "finished_at": None})
    changed_claims = deepcopy(complete["report_claims"])
    changed_claims["claim_1"]["statement"] = "A changed claim must receive a new audit."
    with pytest.raises(ValueError, match="terminal"):
        apply_update(complete, {"report_claims": changed_claims})


def test_langgraph_uses_registered_merge_and_overwrite_contracts():
    state = initial_state(ResearchRequest(question="Reducer wiring smoke test"))
    event = RunEvent(id="event_1", kind="fixture", message="Reducer smoke test")
    payload = event.model_dump(mode="json")

    def first(_state):
        return {"events": {"event_1": payload}, "attempted_query_keys": ["query_b", "query_a"]}

    def replay(_state):
        return {"events": {"event_1": payload}, "attempted_query_keys": ["query_a"]}

    graph = StateGraph(ResearchState)
    graph.add_node("first", first)
    graph.add_node("replay", replay)
    graph.add_edge(START, "first")
    graph.add_edge("first", "replay")
    graph.add_edge("replay", END)
    result = validate_state(graph.compile().invoke(state))
    assert len(result["events"]) == 1
    assert result["attempted_query_keys"] == ["query_a", "query_b"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_records", []),
        ("source_records", {"broken": "scalar"}),
        ("calls", {"broken": None}),
        ("evidence_store", {"broken": []}),
        ("attempted_query_keys", [1]),
    ],
)
def test_malformed_partial_updates_fail_as_validation_errors(populated_state, field, value):
    with pytest.raises(ValueError):
        apply_update(populated_state, {field: value})


def test_evidence_limits_count_utf8_bytes_not_characters(populated_state):
    candidate = deepcopy(populated_state)
    passage = candidate["evidence_store"]["evidence_1"]["passage"]
    assert len(passage.encode("utf-8")) > len(passage)
    candidate["budget"]["max_evidence_bytes"] = len(passage)
    with pytest.raises(ValidationError, match="byte limit"):
        validate_state(candidate)


def test_model_copy_cannot_bypass_boundary_validation(populated_state):
    from evidenceforge.schemas import SourceRecord

    source = SourceRecord.model_validate(populated_state["source_records"]["source_1"])
    candidate = deepcopy(populated_state)
    candidate["source_records"]["source_1"] = source.model_copy(update={"url": None})
    with pytest.raises(ValidationError, match="URL"):
        validate_state(candidate)


def test_report_sources_cannot_diverge_from_claim_support(populated_state):
    patch = draft_patch()
    patch["draft_report"]["source_ids"] = []
    with pytest.raises(ValidationError, match="sources must match"):
        apply_update(populated_state, patch)
