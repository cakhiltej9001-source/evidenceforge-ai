"""Offline retrieval graph, provenance, durable receipts and bounded failures."""

import asyncio
import json
from copy import deepcopy
from datetime import timedelta

import pytest

from evidenceforge.graph.state import StateSnapshot, apply_update
from evidenceforge.nodes.extraction import EvidenceExtractor
from evidenceforge.nodes.sources import SourceProcessor
from evidenceforge.retrieval.contracts import (
    RetrievalBatch,
    RetrievalFailure,
    RetrievalOptions,
    RetrievedSource,
)
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType, utc_now
from evidenceforge.services.planning import PlanningService
from evidenceforge.services.retrieval import RetrievalService

REQUEST = ResearchRequest(question="Compare solar and wind electricity output.")


def planned(budget=None):
    return asyncio.run(PlanningService().plan(REQUEST, budget))


def retrieve(tmp_path, response=None, options=None, budget=None, adapter=None):
    adapter = adapter or FixtureRetrievalAdapter(response)
    service = RetrievalService(tmp_path, {SourceType.WEB: adapter}, options)
    return asyncio.run(service.run(REQUEST, budget)), adapter, service


def batch(content, url="https://example.org/source", scope="full_text"):
    return RetrievalBatch(
        results=(
            RetrievedSource(
                title="Synthetic source", url=url, content=content, content_scope=scope
            ),
        )
    )


def test_offline_graph_exact_spans_duplicate_provenance_and_unknown_usage(tmp_path):
    state, adapter, service = retrieve(tmp_path)
    snapshot = StateSnapshot.model_validate(state)
    assert state["run_status"] == "running"
    assert state["iteration_count"] == 1 and state["search_queries"] == []
    assert adapter.calls == 3
    assert len(state["source_records"]) == 1 and len(state["source_acquisitions"]) == 3
    assert len(state["evidence_store"]) == 2
    assert {e["reason"] for e in state["rejected_evidence"].values()} == {"duplicate", "irrelevant"}
    artifacts, ledger = service.components(state)
    for item in snapshot.evidence_store.values():
        assert len(item.acquisition_ids) == len(item.question_ids) == 3
        text = artifacts.read(snapshot.raw_result_refs[item.locator.snapshot_id])
        assert text[item.locator.start_offset : item.locator.end_offset] == item.passage
    assert len(ledger.records()) == len(state["calls"]) == 3
    assert all(c["status"] == "completed" for c in state["calls"].values())
    assert all(r["status"] == "settled" for r in state["reservations"].values())
    assert all(
        u["estimated_cost_usd"] is None and u["search_credits"] is None
        for u in state["usage"].values()
    )
    assert state["final_report"] is state["draft_report"] is None
    assert len(state["attempted_query_keys"]) == 3
    assert json.loads(json.dumps(state)) == state


def test_completed_receipts_reuse_response_without_new_search_and_finished_pass_replay(tmp_path):
    adapter = FixtureRetrievalAdapter()
    service = RetrievalService(tmp_path, {SourceType.WEB: adapter})
    initial = planned()
    first = asyncio.run(service.retrieve(initial))
    second = asyncio.run(service.retrieve(initial))
    assert adapter.calls == 3
    for channel in ("source_records", "source_acquisitions", "evidence_store", "calls", "usage"):
        assert first[channel] == second[channel]
    assert asyncio.run(service.retrieve(first)) == first


@pytest.mark.parametrize("category", ["authentication", "rate_limit", "provider"])
def test_failed_search_has_typed_error_settled_reservation_no_retry_or_raw_detail(
    tmp_path, category
):
    class Adapter(FixtureRetrievalAdapter):
        async def search(self, query, options):
            self.calls += 1
            raise RetrievalFailure(category)

    state, adapter, service = retrieve(tmp_path, adapter=Adapter())
    assert adapter.calls == 3 and state["iteration_count"] == 1
    assert not state["evidence_store"] and not state["source_records"]
    assert {e["category"] for e in state["tool_errors"].values()} == {category}
    assert all(c["status"] == "failed" for c in state["calls"].values())
    assert all(r["status"] == "settled" for r in state["reservations"].values())
    assert len(service.components(state)[1].records()) == 3


def test_empty_search_is_completed_without_invented_evidence(tmp_path):
    state, adapter, _ = retrieve(tmp_path, response={"results": []})
    assert adapter.calls == 3
    assert state["iteration_count"] == 1 and not state["tool_errors"]
    assert not state["evidence_store"] and not state["source_records"]
    assert all(c["status"] == "completed" for c in state["calls"].values())


@pytest.mark.parametrize(
    "response",
    [
        "private raw provider failure",
        {
            "results": [
                {"title": "Secret", "url": "https://user:password@example.org", "content": "solar"}
            ]
        },
        {
            "results": [
                {
                    "title": "Secret",
                    "url": "https://example.org",
                    "content": "solar",
                    "owner_scope": "other",
                }
            ]
        },
        {
            "results": [
                {
                    "title": "Secret",
                    "url": "https://example.org",
                    "content": "solar",
                    "source_type": "document",
                }
            ]
        },
        {"results": [{"title": "Secret", "url": "file:///private.txt", "content": "solar"}]},
        {"results": [], "unexpected_secret": "secret_value"},
    ],
)
def test_malformed_or_private_response_does_not_enter_state(tmp_path, response):
    state, _, _ = retrieve(tmp_path, response=response)
    assert {e["category"] for e in state["tool_errors"].values()} == {"schema"}
    assert not state["source_records"] and not state["evidence_store"]
    assert "password" not in json.dumps(state) and "secret_value" not in json.dumps(state)


def test_result_count_and_response_size_caps(tmp_path):
    result = {"title": "Fixture", "url": "https://example.org", "content": "solar"}
    state, _, _ = retrieve(
        tmp_path / "count",
        response={"results": [result] * 2},
        options=RetrievalOptions(max_results=1),
    )
    assert {e["category"] for e in state["tool_errors"].values()} == {"schema"}
    state, _, _ = retrieve(
        tmp_path / "bytes",
        response=batch("solar " * 100),
        options=RetrievalOptions(max_response_bytes=100),
    )
    assert {e["category"] for e in state["tool_errors"].values()} == {"schema"}


@pytest.mark.parametrize(
    "content,reason,options",
    [
        ("", "unavailable_content", RetrievalOptions()),
        ("solar " * 100, "content_limit", RetrievalOptions(max_source_bytes=30)),
        ("solar " * 100, "snapshot_limit", RetrievalOptions(max_artifact_bytes=1000)),
    ],
)
def test_source_rejection_reasons_are_retained(tmp_path, content, reason, options):
    # For the artifact cap, one response fits but a separate text snapshot does not.
    budget = BudgetLimits(max_queries_per_pass=1, max_subquestions=1)
    state, _, _ = retrieve(tmp_path, response=batch(content), options=options, budget=budget)
    assert reason in {e["reason"] for e in state["rejected_evidence"].values()}
    assert not state["evidence_store"]


def test_lexical_irrelevance_and_excerpt_labeling(tmp_path):
    state, _, _ = retrieve(
        tmp_path / "unrelated", response=batch("A recipe for apple pie and cinnamon.")
    )
    assert not state["evidence_store"]
    assert {e["reason"] for e in state["rejected_evidence"].values()} == {"irrelevant"}, [
        e["category"] for e in state["tool_errors"].values()
    ]
    state, _, _ = retrieve(
        tmp_path / "excerpt", response=batch("solar electricity output", scope="search_excerpt")
    )
    assert state["evidence_store"]
    assert {s["access_status"] for s in state["source_records"].values()} == {"excerpt_only"}
    assert {a["content_scope"] for a in state["source_acquisitions"].values()} == {"search_excerpt"}


def test_evidence_byte_count_and_per_source_caps(tmp_path):
    content = "  solar electricity output: café.\n\nwind electricity output depends on wind."
    state, _, _ = retrieve(
        tmp_path / "count", response=batch(content), budget=BudgetLimits(max_evidence_count=1)
    )
    assert len(state["evidence_store"]) == 1, [e["category"] for e in state["tool_errors"].values()]
    assert "evidence_limit" in {e["reason"] for e in state["rejected_evidence"].values()}
    state, _, _ = retrieve(
        tmp_path / "bytes", response=batch(content), budget=BudgetLimits(max_evidence_bytes=5)
    )
    assert not state["evidence_store"]
    assert "evidence_limit" in {e["reason"] for e in state["rejected_evidence"].values()}
    state, _, _ = retrieve(
        tmp_path / "passages",
        response=batch(content),
        options=RetrievalOptions(max_passages_per_source=1),
    )
    assert len(state["evidence_store"]) == 1, [e["category"] for e in state["tool_errors"].values()]


def test_snapshot_tampering_rejects_extraction(tmp_path):
    service = RetrievalService(tmp_path)
    state = planned()
    artifacts, ledger = service.components(state)
    patch = asyncio.run(
        SourceProcessor(service.adapters, artifacts, ledger, service.options)(state)
    )
    state = apply_update(state, patch)
    reference = next(
        iter(StateSnapshot.model_validate(state).source_acquisitions.values())
    ).snapshot_id
    ref = StateSnapshot.model_validate(state).raw_result_refs[reference]
    (artifacts.root / ref.storage_key).write_text("tampered source", encoding="utf-8")
    result = apply_update(state, EvidenceExtractor(artifacts, service.options)(state))
    assert not result["evidence_store"]
    assert {e["reason"] for e in result["rejected_evidence"].values()} == {"parse_failed"}


def test_timeout_is_bounded_and_receipts_are_not_retried(tmp_path):
    class Adapter(FixtureRetrievalAdapter):
        async def search(self, query, options):
            self.calls += 1
            await asyncio.Event().wait()

    state, adapter, _ = retrieve(
        tmp_path, adapter=Adapter(), options=RetrievalOptions(timeout_seconds=0.02)
    )
    assert adapter.calls == 3
    assert {e["category"] for e in state["tool_errors"].values()} == {"timeout"}
    assert all(c["status"] == "failed" for c in state["calls"].values())


def test_dispatch_reserves_before_search_and_enforces_concurrency(tmp_path):
    async def scenario():
        service = RetrievalService(tmp_path)
        state = await PlanningService().plan(REQUEST, BudgetLimits(max_concurrency=2))
        artifacts, ledger = service.components(state)
        active, peak = 0, 0
        two_started = asyncio.Event()

        class Adapter(FixtureRetrievalAdapter):
            async def search(self, query, options):
                nonlocal active, peak
                assert len(ledger.records()) >= 1
                assert any(r.call.status == "pending" for r in ledger.records().values())
                active += 1
                peak = max(active, peak)
                if active == 2:
                    two_started.set()
                await two_started.wait()
                await asyncio.sleep(0)
                response = await super().search(query, options)
                active -= 1
                return response

        adapter = Adapter()
        before = deepcopy(state)
        patch = await SourceProcessor(
            {SourceType.WEB: adapter}, artifacts, ledger, service.options
        )(state)
        assert state == before
        assert peak == 2 and adapter.calls == 3
        assert apply_update(state, patch)["iteration_count"] == 1

    asyncio.run(scenario())


def test_cancelled_pending_receipt_becomes_ambiguous_without_a_duplicate_call(tmp_path):
    async def scenario():
        entered = asyncio.Event()

        class Adapter(FixtureRetrievalAdapter):
            async def search(self, query, options):
                self.calls += 1
                entered.set()
                await asyncio.Event().wait()

        initial = await PlanningService().plan(REQUEST, BudgetLimits(max_queries_per_pass=1))
        service = RetrievalService(tmp_path)
        artifacts, ledger = service.components(initial)
        adapter = Adapter()
        processor = SourceProcessor({SourceType.WEB: adapter}, artifacts, ledger, service.options)
        task = asyncio.create_task(processor(initial))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert next(iter(ledger.records().values())).call.status == "pending"
        result = apply_update(initial, await processor(initial))
        assert adapter.calls == 1
        assert {c["status"] for c in result["calls"].values()} == {"ambiguous"}
        assert {e["category"] for e in result["tool_errors"].values()} == {"internal"}

    asyncio.run(scenario())


def test_search_allowance_race_does_not_dispatch_excess_calls(tmp_path):
    initial = planned(BudgetLimits(max_searches=1))
    existing = deepcopy(initial["search_queries"][0])
    additional = [
        {**existing, "id": f"extra_query_{i}", "text": f"solar output {i}"} for i in range(2)
    ]
    initial = apply_update(
        initial,
        {
            "search_queries": initial["search_queries"] + additional,
            "query_records": {q["id"]: q for q in additional},
        },
    )
    adapter = FixtureRetrievalAdapter()
    result = asyncio.run(RetrievalService(tmp_path, {SourceType.WEB: adapter}).retrieve(initial))
    assert adapter.calls == len(result["calls"]) == 1
    assert len(result["attempted_query_keys"]) == 1
    assert [e["category"] for e in result["tool_errors"].values()] == ["budget", "budget"]


def test_expired_run_and_unknown_live_cost_ceiling_make_no_calls(tmp_path):
    initial = planned(BudgetLimits(max_elapsed_seconds=1))
    initial = apply_update(initial, {"started_at": (utc_now() - timedelta(seconds=10)).isoformat()})
    adapter = FixtureRetrievalAdapter()
    state = asyncio.run(
        RetrievalService(tmp_path / "time", {SourceType.WEB: adapter}).retrieve(initial)
    )
    assert adapter.calls == 0 and not state["calls"]
    assert {e["category"] for e in state["tool_errors"].values()} == {"budget"}

    class LiveAdapter(FixtureRetrievalAdapter):
        is_live = True

    live = LiveAdapter()
    state, _, _ = retrieve(tmp_path / "cost", adapter=live, budget=BudgetLimits(max_cost_usd=0.01))
    assert live.calls == 0
    assert {e["category"] for e in state["tool_errors"].values()} == {"budget"}


def test_unsupported_source_is_disclosed_without_attempt_or_reservation(tmp_path):
    initial = planned()
    service = RetrievalService(tmp_path, adapters={})
    result = asyncio.run(service.retrieve(initial))
    assert not result["calls"] and not result["attempted_query_keys"]
    assert {e["category"] for e in result["tool_errors"].values()} == {"provider"}


def test_completed_receipts_are_reused_after_dispatch_deadline(tmp_path):
    initial = planned(BudgetLimits(max_elapsed_seconds=60))
    adapter = FixtureRetrievalAdapter()
    service = RetrievalService(tmp_path, {SourceType.WEB: adapter})
    first = asyncio.run(service.retrieve(initial))
    expired = apply_update(
        initial,
        {
            "started_at": (utc_now() - timedelta(seconds=120)).isoformat(),
        },
    )
    reused = asyncio.run(service.retrieve(expired))
    assert adapter.calls == 3
    assert not reused["tool_errors"]
    assert reused["evidence_store"] == first["evidence_store"]
