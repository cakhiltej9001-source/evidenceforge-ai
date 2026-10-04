"""Paid call replay, restart budgets and approval without live network."""

import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from evidenceforge.models.gemini import GeminiResearchModel, provider_schema
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.nodes.approval import PlanDecision
from evidenceforge.planning import ModelUnavailable, PlanDraft, QueryGenerationRequest
from evidenceforge.research import CoverageInput, CriticInput, ResearchOptions, SynthesisInput
from evidenceforge.schemas import BudgetLimits, ResearchRequest
from evidenceforge.services.research import ResearchService
from evidenceforge.storage.model_calls import ModelCallLedger

QUESTION = "Compare solar and wind electricity output."
PLAN = {
    "questions": [
        {"question": "What determines solar output?", "acceptance_criteria": ["solar output"]}
    ]
}


def reply(value):
    return {
        "candidates": [
            {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(value)}]}}
        ],
        "usageMetadata": {"promptTokenCount": 20, "totalTokenCount": 80},
    }


def adapter(handler, budget=None):
    return GeminiResearchModel(
        "gemini-3.5-flash-lite",
        SecretStr("private-test-key"),
        budget or BudgetLimits(),
        transport=httpx.MockTransport(handler),
    )


def test_completed_call_replay_uses_no_network_and_preserves_budget(tmp_path):
    seen = []
    budget = BudgetLimits(max_model_calls=3)

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=reply(PLAN))

    first = adapter(handler, budget)
    first.bind_run(tmp_path, "alice", "run_test", budget, existing=False)
    result = asyncio.run(first.plan(ResearchRequest(question=QUESTION), max_questions=1))
    second = adapter(lambda request: pytest.fail("No repeated paid request"), budget)
    second.bind_run(tmp_path, "alice", "run_test", budget, existing=True)
    assert asyncio.run(second.plan(ResearchRequest(question=QUESTION), max_questions=1)) == result
    assert len(seen) == len(second.observations) == 1
    assert second.observations[0]["total_tokens"] == 80
    assert "private-test-key" not in second._ledger.path.read_bytes().decode(errors="ignore")
    with pytest.raises(ModelUnavailable, match="configuration"):
        adapter(handler).bind_run(tmp_path, "alice", "run_test", BudgetLimits(), existing=True)
    with pytest.raises(ModelUnavailable, match="no durable"):
        adapter(handler).bind_run(tmp_path, "bob", "run_test", BudgetLimits(), existing=True)


def test_pending_call_blocks_repeat_and_new_paid_calls(tmp_path):
    budget = BudgetLimits()
    ledger = ModelCallLedger(tmp_path, "alice", "run_crash", "gemini-3.5-flash-lite", budget)
    ledger.reserve("crashed", {"reserved_tokens": 10000, "total_tokens": None})
    restarted = adapter(lambda request: pytest.fail("Unconfirmed charge must not retry"))
    restarted.bind_run(tmp_path, "alice", "run_crash", budget, existing=True)
    with pytest.raises(ModelUnavailable, match="unconfirmed"):
        asyncio.run(restarted.plan(ResearchRequest(question=QUESTION), max_questions=1))
    assert len(restarted.observations) == 1


def test_failed_charge_reservation_survives_restart(tmp_path):
    budget = BudgetLimits(max_total_tokens=18000)
    first = adapter(lambda request: httpx.Response(503), budget)
    first.bind_run(tmp_path, "alice", "run_fail", budget, existing=False)
    with pytest.raises(ModelUnavailable):
        asyncio.run(first.plan(ResearchRequest(question=QUESTION), max_questions=1))
    second = adapter(lambda request: pytest.fail("Failed same call must not retry"), budget)
    second.bind_run(tmp_path, "alice", "run_fail", budget, existing=True)
    with pytest.raises(ModelUnavailable, match="replay is blocked"):
        asyncio.run(second.plan(ResearchRequest(question=QUESTION), max_questions=1))
    assert second._reserved_tokens == first._reserved_tokens
    assert second.observations == first.observations


def test_provider_schema_keeps_full_local_validation():
    wire = provider_schema(PlanDraft.model_json_schema())
    encoded = json.dumps(wire)
    assert "maxLength" not in encoded and "maxItems" not in encoded
    assert wire["$defs"]["QuestionDraft"]["properties"]["importance"]["maximum"] == 1
    assert provider_schema(
        {"type": "string", "pattern": "^(support|counter_evidence|primary_source)$"}
    )["enum"] == ["support", "counter_evidence", "primary_source"]
    with pytest.raises(ValueError):
        PlanDraft.model_validate(
            {"questions": [{"question": "x" * 1001, "acceptance_criteria": ["x"]}]}
        )


def test_paid_plan_edit_approval_and_terminal_reconnect_across_services(tmp_path):
    fixture = FixtureResearchModel()
    seen = []

    async def handler(request):
        data = json.loads(request.content)
        seen.append(data["generationConfig"]["responseJsonSchema"]["title"])
        value = json.loads(data["contents"][0]["parts"][0]["text"])
        title = seen[-1]
        if title == "PlanDraft":
            result = await fixture.plan(ResearchRequest.model_validate(value), max_questions=8)
        elif title == "QueryBatchDraft":
            result = await fixture.generate_queries(QueryGenerationRequest.model_validate(value))
        elif title == "CoverageAssessment":
            result = await fixture.evaluate_coverage(CoverageInput.model_validate(value))
        elif title == "ReportDraft":
            result = await fixture.synthesize(SynthesisInput.model_validate(value))
        else:
            result = await fixture.critique(CriticInput.model_validate(value))
        return httpx.Response(200, json=reply(result))

    def service():
        return ResearchService(
            tmp_path, model=adapter(handler), options=ResearchOptions(require_plan_approval=True)
        )

    first = service()
    paused = asyncio.run(first.run(ResearchRequest(question=QUESTION)))
    assert paused["approval_status"] == "awaiting_approval"
    assert seen == ["PlanDraft"]
    edited = asyncio.run(
        service().edit_plan(paused["thread_id"], PlanDraft.model_validate(PLAN), 1)
    )
    assert edited["plan_version"] == 2 and seen == ["PlanDraft"]
    fresh = service()
    final = asyncio.run(
        fresh.resume(paused["thread_id"], decision=PlanDecision(approved=True, plan_version=2))
    )
    assert final["run_status"] == "completed"
    assert seen == [
        "PlanDraft",
        "QueryBatchDraft",
        "CoverageAssessment",
        "ReportDraft",
        "CriticAssessment",
    ]
    assert len(fresh.model.observations) == 5
    count = len(seen)
    assert asyncio.run(service().resume(paused["thread_id"])) == final
    assert len(seen) == count
