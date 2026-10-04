import json

import pytest
from pydantic import ValidationError

from evidenceforge.identity import new_id, stable_id
from evidenceforge.schemas import (
    ArtifactReference,
    BudgetLimits,
    CallRecord,
    CitationAuditItem,
    CriticVerdict,
    EvidenceItem,
    EvidenceLocator,
    Report,
    ResearchQuestion,
    ResearchRequest,
    SourceRecord,
    UsageRecord,
)


def test_content_identity_canonical_and_owner_sensitive():
    assert stable_id("source", {"url": "u", "hash": "h"}) == stable_id(
        "source", {"hash": "h", "url": "u"}
    )
    assert stable_id("document", "alice", "hash") != stable_id("document", "bob", "hash")
    assert new_id("run") != new_id("run")
    with pytest.raises(ValueError):
        stable_id("../invalid", "data")
    with pytest.raises(ValueError):
        stable_id("source", float("nan"))


@pytest.mark.parametrize(
    "update",
    [
        {"max_research_passes": 0},
        {"max_rewrites": -1},
        {"max_searches": True},
        {"max_total_tokens": "100"},
        {"max_model_calls": 2},
        {"max_cost_usd": float("nan")},
        {"max_cost_usd": float("inf")},
        {"max_cost_usd": True},
        {"misspelled_limit": 12},
    ],
)
def test_invalid_budgets_cannot_silently_change_limits(update):
    with pytest.raises(ValidationError):
        BudgetLimits(**update)


@pytest.mark.parametrize("question", ["", "   ", "\n", "x" * 10001])
def test_request_rejects_empty_or_oversized_questions(question):
    with pytest.raises(ValidationError):
        ResearchRequest(question=question)


def test_questions_need_criteria_and_unique_references():
    with pytest.raises(ValidationError):
        ResearchQuestion(id="q_1", question="Question", acceptance_criteria=())
    with pytest.raises(ValidationError):
        ResearchRequest(question="Question", document_ids=("doc_1", "doc_1"))


def test_exact_passage_preserved_and_round_trips(populated_state):
    payload = populated_state["evidence_store"]["evidence_1"]
    record = EvidenceItem.model_validate(payload)
    assert record.passage == "  Synthetic evidence: café.\n"
    assert EvidenceItem.model_validate_json(record.model_dump_json()) == record
    assert json.loads(record.model_dump_json())["passage"] == record.passage
    with pytest.raises(ValidationError):
        record.passage = "changed"


@pytest.mark.parametrize(
    "locator",
    [
        {"snapshot_id": "snapshot_1"},
        {"snapshot_id": "snapshot_1", "start_offset": 0},
        {"snapshot_id": "snapshot_1", "start_offset": 5, "end_offset": 4},
        {"snapshot_id": "snapshot_1", "page": 0},
    ],
)
def test_missing_or_impossible_locator_rejected(locator):
    with pytest.raises(ValidationError):
        EvidenceLocator(**locator)


def test_passage_offsets_and_scores_validated(populated_state):
    original = populated_state["evidence_store"]["evidence_1"]
    for update in ({"passage": "different"}, {"relevance": 1.5}, {"relevance": True}):
        with pytest.raises(ValidationError):
            EvidenceItem.model_validate({**original, **update})


@pytest.mark.parametrize("storage_key", ["../secret", "a/../b", "/absolute", "C:\\secret", "a//b"])
def test_artifact_keys_cannot_escape_storage(storage_key):
    with pytest.raises(ValidationError):
        ArtifactReference(
            id="snapshot_1",
            content_hash="a" * 64,
            storage_key=storage_key,
            parser_version="1",
            byte_count=1,
        )


@pytest.mark.parametrize(
    "update",
    [
        {"url": None},
        {"url": "file:///secret"},
        {"url": "https://user:password@example.org"},
        {"source_type": "document", "url": None},
    ],
)
def test_sources_need_valid_public_or_scoped_private_locations(populated_state, update):
    with pytest.raises(ValidationError):
        SourceRecord.model_validate({**populated_state["source_records"]["source_1"], **update})


def test_schema_requires_aware_times_and_completed_response():
    common = {
        "id": "call_1",
        "request_hash": "a" * 64,
        "provider": "fixture",
        "kind": "model",
        "status": "completed",
        "started_at": "2026-09-30T00:00:00Z",
    }
    with pytest.raises(ValidationError):
        CallRecord.model_validate(common)
    with pytest.raises(ValidationError):
        CallRecord.model_validate({**common, "status": "pending", "started_at": "2026-09-30"})


def test_unknown_usage_is_not_reported_as_free():
    usage = UsageRecord(id="usage_1", call_id="call_1", provider="fixture", latency_ms=1)
    assert usage.estimated_cost_usd is None
    assert usage.input_tokens is None
    assert usage.model_dump(mode="json")["estimated_cost_usd"] is None
    with pytest.raises(ValidationError):
        UsageRecord(
            id="usage_1",
            call_id="call_1",
            provider="fixture",
            latency_ms=1,
            estimated_cost_usd=0.01,
        )


def test_revision_and_supported_audit_require_actual_details():
    with pytest.raises(ValidationError):
        CriticVerdict(draft_version=1, decision="revise")
    with pytest.raises(ValidationError):
        CitationAuditItem(
            id="audit_1",
            draft_version=1,
            claim_id="claim_1",
            structural_valid=True,
            support="supported",
            rationale="No passage",
        )


def test_report_cannot_include_prose_outside_claim_registry():
    with pytest.raises(ValidationError):
        Report.model_validate(
            {
                "id": "report_1",
                "draft_version": 1,
                "sections": [
                    {"name": "summary", "claim_ids": (), "prose": "Untracked factual assertion"},
                    {"name": "key_findings", "claim_ids": ()},
                ],
            }
        )
