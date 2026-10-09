"""Budget, provenance, rejection and login behavior for production controls."""

import asyncio
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from evidenceforge.auth import LoginGate, fingerprint, password_hash, required, verify_password
from evidenceforge.config import ConfigurationError, Settings
from evidenceforge.evidence.retention import select_evidence
from evidenceforge.graph.state import apply_update, initial_state
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.planning import QueryGenerationRequest
from evidenceforge.research import CoverageInput, CriticInput, ResearchOptions, SynthesisInput
from evidenceforge.retrieval.contracts import RetrievalFailure
from evidenceforge.retrieval.fallback import OrderedSearch
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.node_trace import NodeTrace
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService


class PrimaryFailure(FixtureRetrievalAdapter):
    name = "primary_failure"

    async def search(self, query, options):
        self.calls += 1
        raise RetrievalFailure("authentication")


@pytest.mark.parametrize("search_cap,expected_calls", [(1, 1), (2, 2)])
def test_ordered_fallback_spends_each_search_and_reuses_receipts(
    tmp_path, search_cap, expected_calls
):
    primary, secondary = PrimaryFailure(), FixtureRetrievalAdapter()
    chain = OrderedSearch((primary, secondary))

    def service():
        return ResearchService(
            tmp_path, retrieval=RetrievalService(tmp_path, {SourceType.WEB: chain})
        )

    state = asyncio.run(
        service().run(
            ResearchRequest(question="Compare solar and wind electricity output."),
            BudgetLimits(
                max_subquestions=1,
                max_queries_per_pass=1,
                max_research_passes=1,
                max_searches=search_cap,
                max_attempts_per_call=1,
            ),
        )
    )
    assert len(state["calls"]) == expected_calls
    assert primary.calls == 1
    assert secondary.calls == search_cap - 1
    if search_cap == 2:
        assert state["source_records"]
        assert all(s["provider"] == secondary.name for s in state["source_records"].values())
    replay = asyncio.run(service().resume(state["thread_id"]))
    assert replay == state
    assert primary.calls + secondary.calls == expected_calls


def test_retention_evicts_lower_score_preserves_snapshot_and_pinned_claim(populated_state):
    state = deepcopy(populated_state)
    state["budget"]["max_evidence_count"] = 1
    old_id = next(iter(state["evidence_store"]))
    old = state["evidence_store"][old_id]
    old["relevance"] = 0.2
    incoming = deepcopy(old)
    incoming.update(id="evidence_better", relevance=0.9)
    selected = apply_update(state, select_evidence(state, {incoming["id"]: incoming}, {}))
    assert set(selected["evidence_store"]) == {"evidence_better"}
    assert selected["raw_result_refs"] == state["raw_result_refs"]
    assert any(r["candidate_id"] == old_id for r in selected["rejected_evidence"].values())
    state["report_claims"] = {
        "claim_pinned": {
            "id": "claim_pinned",
            "statement": old["passage"],
            "kind": "fact",
            "question_ids": old["question_ids"],
            "evidence_ids": [old_id],
            "qualifiers": [],
        }
    }
    pinned = apply_update(state, select_evidence(state, {incoming["id"]: incoming}, {}))
    assert set(pinned["evidence_store"]) == {old_id}


@pytest.mark.parametrize("category", ["gibberish", "non_research", "manipulation", "vague"])
def test_semantic_rejection_uses_one_call_and_no_search(tmp_path, category):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": json.dumps({"category": category})}]},
                    }
                ]
            },
        )

    budget = BudgetLimits(max_model_calls=6)
    model = GeminiResearchModel(
        "synthetic-model", SecretStr("test-key"), budget, transport=httpx.MockTransport(respond)
    )
    adapter = FixtureRetrievalAdapter()
    state = asyncio.run(
        ResearchService(
            tmp_path,
            model=model,
            retrieval=RetrievalService(tmp_path, {SourceType.WEB: adapter}),
            options=ResearchOptions(production_policy_version=1),
        ).run(ResearchRequest(question="A request requiring semantic review."), budget)
    )
    assert state["stop_reason"] == "input_rejected"
    assert len(requests) == 1 and adapter.calls == 0
    assert any(e["kind"] == "input_review_" + category for e in state["events"].values())


def test_semantic_acceptance_completes_six_stage_workflow_and_replays(tmp_path):
    fixture = FixtureResearchModel()
    seen_titles = []

    async def respond(request):
        payload = json.loads(request.content)
        title = payload["generationConfig"]["responseJsonSchema"]["title"]
        value = json.loads(payload["contents"][0]["parts"][0]["text"])
        seen_titles.append(title)
        if title == "SemanticDecision":
            result = {"category": "research"}
        elif title == "PlanDraft":
            result = await fixture.plan(ResearchRequest.model_validate(value), max_questions=1)
        elif title == "QueryBatchDraft":
            result = await fixture.generate_queries(QueryGenerationRequest.model_validate(value))
        elif title == "CoverageAssessment":
            result = await fixture.evaluate_coverage(CoverageInput.model_validate(value))
        elif title == "QuoteSelectionDraft":
            result = {
                "claims": [
                    {"evidence_id": item["id"], "question_ids": item["question_ids"]}
                    for item in value["evidence"]
                ]
            }
        elif title == "ReportDraft":
            result = await fixture.synthesize(SynthesisInput.model_validate(value))
        else:
            result = await fixture.critique(CriticInput.model_validate(value))
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(result)}]}}
                ],
                "usageMetadata": {"promptTokenCount": 20, "totalTokenCount": 80},
            },
        )

    budget = BudgetLimits(
        max_subquestions=1,
        max_queries_per_pass=1,
        max_research_passes=1,
        max_searches=1,
        max_model_calls=6,
        max_attempts_per_call=1,
    )
    model = GeminiResearchModel(
        "synthetic-model", SecretStr("test-key"), budget, transport=httpx.MockTransport(respond)
    )
    adapter = FixtureRetrievalAdapter()
    service = ResearchService(
        tmp_path,
        model=model,
        retrieval=RetrievalService(tmp_path, {SourceType.WEB: adapter}),
        options=ResearchOptions(production_policy_version=1),
    )
    state = asyncio.run(
        service.run(ResearchRequest(question="Compare solar and wind electricity output."), budget)
    )
    assert state["run_status"] == "completed"
    assert seen_titles == [
        "SemanticDecision",
        "PlanDraft",
        "QueryBatchDraft",
        "CoverageAssessment",
        "QuoteSelectionDraft",
        "CriticAssessment",
    ]
    assert len(model.observations) == 6
    assert adapter.calls == 1
    trace = next((tmp_path / "traces").glob("*.jsonl")).read_text(encoding="utf-8")
    assert "test-key" not in trace and "Compare solar" not in trace
    replay = asyncio.run(service.resume(state["thread_id"]))
    assert replay == state
    assert len(seen_titles) == 6


def test_trace_is_bounded_and_metadata_default(tmp_path):
    path = tmp_path / "trace.jsonl"
    trace = NodeTrace(path)
    state = initial_state(ResearchRequest(question="PRIVATE_SENTINEL subject"))
    result = asyncio.run(
        trace.wrap("planner", lambda value: {"private": "PRIVATE_SENTINEL"})(state)
    )
    assert result["private"] == "PRIVATE_SENTINEL"
    assert "PRIVATE_SENTINEL" not in path.read_text()
    record = json.loads(path.read_text())
    assert record["node"] == "planner" and record["duration_seconds"] >= 0
    capped = NodeTrace(tmp_path / "tiny.jsonl", max_bytes=1)
    asyncio.run(capped.wrap("planner", lambda value: {})(state))
    assert capped.omitted == 1 and not capped.path.exists()


def test_hosted_login_fails_closed_hashes_and_throttles(monkeypatch):
    settings = Settings()
    monkeypatch.setenv("RENDER", "true")
    assert required(settings)
    with pytest.raises(ConfigurationError):
        fingerprint(settings)
    password = "test-password-long-enough"
    encoded = password_hash(password)
    assert verify_password(password, encoded)
    assert not verify_password("wrong", encoded)
    configured = settings.model_copy(update={"auth_password_hash": SecretStr(encoded)})
    gate = LoginGate()
    assert gate.check("admin", password, configured)
    for _ in range(5):
        assert not gate.check("admin", "wrong", configured)
    assert not gate.check("admin", password, configured)
    assert encoded not in str(configured.model_dump())


def test_gateway_keeps_health_public_and_protects_other_routes():
    root = Path(__file__).parents[1]
    auth = (root / "Caddyfile.auth").read_text(encoding="utf-8")
    entrypoint = (root / "scripts" / "container_entrypoint.sh").read_text(encoding="utf-8")
    assert "path /_stcore/health" in auth
    assert "basic_auth" in auth and "reverse_proxy 127.0.0.1" in auth
    assert "CADDY_AUTH_PASSWORD_HASH" in entrypoint
    assert "CADDY_AUTH_REQUIRED" in entrypoint
