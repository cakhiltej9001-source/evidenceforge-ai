"""Local immutable artifacts and transactional receipt invariants."""

import hashlib
from copy import deepcopy

import pytest

from evidenceforge.nodes.common import record_data
from evidenceforge.retrieval.contracts import ArtifactFailure, CallReceipt, RetrievalFailure
from evidenceforge.schemas import BudgetLimits, BudgetReservation, CallRecord, UsageRecord, utc_now
from evidenceforge.storage.artifacts import ArtifactStore
from evidenceforge.storage.calls import CallLedger


def receipt(identifier="call_a", owner="local", run="run_a"):
    return CallReceipt(
        owner_scope=owner,
        run_id=run,
        call=CallRecord(
            id=identifier,
            request_hash="a" * 64,
            provider="fixture",
            kind="search",
            status="pending",
            started_at=utc_now(),
        ),
        reservation=BudgetReservation(
            id=f"reservation_{identifier}", call_id=identifier, searches=1
        ),
    )


def test_artifact_preserves_utf8_replays_and_rejects_scope_or_tampering(tmp_path):
    store = ArtifactStore(tmp_path, "local", "run_a", 100)
    text = "  solar café.\n"
    ref = store.put(text, "text_v1")
    assert ref.byte_count == len(text.encode("utf-8"))
    assert ref.content_hash == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert store.read(ref) == text
    assert store.put(text, "text_v1") == ref
    with pytest.raises(ArtifactFailure):
        ArtifactStore(tmp_path, "other", "run_a", 100).read(ref)
    (tmp_path / ref.storage_key).write_text("corruption", encoding="utf-8")
    with pytest.raises(ArtifactFailure):
        store.read(ref)
    with pytest.raises(ArtifactFailure):
        store.put(text, "text_v1")


def test_artifact_count_bytes_are_bounded_before_write(tmp_path):
    store = ArtifactStore(tmp_path, "local", "run_a", 5)
    store.put("café", "text_v1")
    with pytest.raises(ArtifactFailure):
        store.put("x", "text_v1")
    assert sum(p.stat().st_size for p in store.directory.glob("*.txt")) == 5
    with pytest.raises(ArtifactFailure):
        store._path("../private.txt")


def test_ledger_reserves_atomically_replays_and_preserves_recorded_usage(tmp_path):
    ledger = CallLedger(tmp_path / "calls", "local", "run_a")
    first = receipt()
    assert ledger.reserve(first, BudgetLimits(max_searches=1)) == (first, True)
    assert ledger.reserve(first, BudgetLimits(max_searches=1)) == (first, False)
    with pytest.raises(RetrievalFailure, match="operation failed"):
        ledger.reserve(receipt("call_b"), BudgetLimits(max_searches=1))
    store = ArtifactStore(tmp_path / "artifacts", "local", "run_a", 100)
    ref = store.put('{"results":[]}', "response_v1")
    complete = CallReceipt.model_validate(
        {
            **first.model_dump(),
            "call": {
                **first.call.model_dump(),
                "status": "completed",
                "revision": 2,
                "finished_at": utc_now(),
                "response_artifact_id": ref.id,
            },
            "reservation": {**first.reservation.model_dump(), "status": "settled"},
            "response": ref,
            "usage": UsageRecord(
                id="usage_a", call_id=first.call.id, provider="fixture", latency_ms=1.0
            ),
        }
    )
    ledger.finish(complete)
    ledger.finish(complete)
    reopened = CallLedger(tmp_path / "calls", "local", "run_a")
    assert reopened.records()[first.call.id] == complete
    with pytest.raises(ValueError, match="roll back"):
        ledger.finish(first)
    altered = CallReceipt.model_validate(
        {
            **complete.model_dump(),
            "usage": {**complete.usage.model_dump(), "latency_ms": 2.0},
        }
    )
    with pytest.raises(ValueError, match="usage"):
        ledger.finish(altered)
    assert ledger.records()[first.call.id] == complete


def test_ledger_scope_request_conflicts_and_external_search_allowance(tmp_path):
    ledger = CallLedger(tmp_path, "local", "run_a")
    with pytest.raises(ValueError, match="scope"):
        ledger.reserve(receipt(owner="other"), BudgetLimits())
    first = receipt()
    ledger.reserve(first, BudgetLimits())
    changed = deepcopy(first.model_dump())
    changed["call"]["request_hash"] = "b" * 64
    with pytest.raises(ValueError, match="identity"):
        ledger.reserve(CallReceipt.model_validate(changed), BudgetLimits())
    with pytest.raises(RetrievalFailure):
        ledger.reserve(receipt("call_b"), BudgetLimits(max_searches=3), extra_searches=2)
    assert record_data(ledger.records()[first.call.id].call)["status"] == "pending"
