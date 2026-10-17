"""Review payload bounds, checkpoint compatibility and unsent-request accounting."""

import asyncio
import json
from copy import deepcopy

import httpx
import pytest
from pydantic import SecretStr
from test_report_recovery import business_report

from evidenceforge.evidence.deduplication import working_evidence
from evidenceforge.graph.state import StateSnapshot, apply_update, initial_state
from evidenceforge.identity import stable_id
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.nodes.common import blocked_model_patch
from evidenceforge.nodes.quality import Critic, QualityNode, compact_critic_input
from evidenceforge.planning import ModelBudgetExceeded, ModelUnavailable
from evidenceforge.research import CriticInput, ResearchOptions
from evidenceforge.schemas import BudgetLimits, ReportSection, ResearchRequest, RunStatus
from evidenceforge.services.failures import public_failures
from evidenceforge.services.observability import public_timeline
from evidenceforge.services.research import ResearchService
from evidenceforge.services.usage import usage_summary
from evidenceforge.storage.model_calls import ModelCallLedger, ModelReceipt, model_usage


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory):
    passage = "An AI business begins with customer interviews and a small pilot."
    state = business_report(
        tmp_path_factory.mktemp("review-input"),
        [passage, passage, "An AI business checks demand before scaling the product."],
    )
    return StateSnapshot.model_validate(state)


def large_snapshot(snapshot):
    evidence = dict(snapshot.evidence_store)
    template = next(iter(evidence.values()))
    for index in range(38):
        passage = f"Synthetic unused context {index}. " + "background material " * 50
        item = template.model_copy(
            update={
                "id": stable_id("evidence", "unused-context", index),
                "passage": passage,
                "locator": template.locator.model_copy(
                    update={"start_offset": 0, "end_offset": len(passage)}
                ),
            }
        )
        evidence[item.id] = item
    return snapshot.model_copy(update={"evidence_store": evidence})


def test_compact_review_keeps_every_claim_and_coverage_reference(snapshot):
    large = large_snapshot(snapshot)
    before = large.model_dump_json()
    request = compact_critic_input(large)
    required = {eid for c in large.report_claims.values() for eid in c.evidence_ids}
    required.update(eid for c in large.coverage_by_question.values() for eid in c.evidence_ids)
    assert {e.id for e in request.evidence} == required
    assert request.claims == tuple(large.report_claims.values())
    assert request.coverage == tuple(large.coverage_by_question.values())
    assert request.request == large.request and request.questions == large.research_questions
    assert any(len(c.evidence_ids) > 1 for c in request.claims)
    assert large.model_dump_json() == before
    working = working_evidence(large.evidence_store.values())
    old = CriticInput(
        report=large.draft_report,
        claims=tuple(large.report_claims.values()),
        evidence=working.evidence,
        duplicate_evidence=working.duplicates,
        coverage=tuple(large.coverage_by_question.values()),
    )
    assert len(request.model_dump_json()) < len(old.model_dump_json()) / 2


def test_conflicting_measurements_remain_even_when_not_selected(tmp_path):
    state = business_report(
        tmp_path,
        [
            "AI business electricity output was 100 GWh in 2024 "
            "for all plants under standard operation.",
            "AI business electricity output was 200 GWh in 2024 "
            "for all plants under standard operation.",
        ],
    )
    s = StateSnapshot.model_validate(state)
    assert s.comparisons
    claim = next(iter(s.report_claims.values()))
    report = s.draft_report.model_copy(
        update={
            "sections": (
                ReportSection(name="summary", claim_ids=(claim.id,)),
                ReportSection(name="key_findings", claim_ids=(claim.id,)),
            )
        }
    )
    s = s.model_copy(
        update={
            "draft_report": report,
            "report_claims": {claim.id: claim},
            "coverage_by_question": {
                qid: c.model_copy(update={"evidence_ids": claim.evidence_ids})
                for qid, c in s.coverage_by_question.items()
            },
        }
    )
    required = {
        s.propositions[pid].evidence_id
        for c in s.comparisons.values()
        if c.relationship == "contradicts"
        for pid in (c.left_id, c.right_id)
    }
    assert required - set(claim.evidence_ids)
    assert required.issubset({e.id for e in compact_critic_input(s).evidence})


@pytest.mark.parametrize("policy", [3, 4])
def test_critic_version_controls_input_without_mutating_evidence(snapshot, policy):
    class Capture(FixtureResearchModel):
        captured = None

        async def critique(self, request):
            self.captured = request
            return {"decision": "approved", "revision_brief": []}

    large = large_snapshot(snapshot).model_copy(
        update={
            "run_status": RunStatus.RUNNING,
            "finished_at": None,
            "final_report": None,
            "stop_reason": None,
        }
    )
    model = Capture()
    state = large.model_dump(mode="json")
    patch = asyncio.run(Critic(model, ResearchOptions(production_policy_version=policy))(state))
    assert "critic_verdict" in patch and model.captured is not None
    data = model.captured.model_dump(mode="json")
    if policy == 3:
        assert "request" not in data and "questions" not in data
        assert len(model.captured.evidence) == len(
            working_evidence(large.evidence_store.values()).evidence
        )
    else:
        assert data["request"]["question"] == large.request.question
        assert len(model.captured.evidence) < len(large.evidence_store)
    assert state == large.model_dump(mode="json")


def receipts(count=4):
    return model_usage(
        [
            ModelReceipt(
                id=f"synthetic_{i}",
                status="succeeded",
                observation={
                    "model": "synthetic-model",
                    "input_tokens": 10,
                    "output_tokens_including_thinking": 20,
                    "total_tokens": 30,
                    "reserved_tokens": 100,
                },
            )
            for i in range(count)
        ]
    )


@pytest.mark.parametrize("reason", ["token_limit", "model_call_limit"])
def test_local_budget_block_is_not_an_unknown_charge(reason):
    state = apply_update(
        initial_state(ResearchRequest(question="Synthetic review")),
        {"planning_attempts": 2, "quality_attempts": 2},
    )
    before = deepcopy(state)
    patch = QualityNode(FixtureResearchModel(), ResearchOptions()).failure(
        state, "critic", ModelBudgetExceeded(reason)
    )
    result = apply_update(state, patch)
    assert result["stop_reason"] == reason
    assert next(iter(result["tool_errors"].values()))["category"] == "budget"
    usage = usage_summary(result, provider_usage=receipts())
    assert usage["model_attempts"] == 5 and usage["paid_model_calls"] == 4
    assert usage["model_requests_blocked_locally"] == 1
    assert usage["token_usage_unknown_records"] == 0
    assert state == before
    assert any("blocked locally" in e["step"] for e in public_timeline(result))
    if reason == "token_limit":
        message = public_failures(result)[0]["message"]
        assert "blocked locally" in message and "before contacting Gemini" in message


def test_unexplained_failure_still_has_unknown_usage():
    state = apply_update(
        initial_state(ResearchRequest(question="Synthetic review")),
        {"planning_attempts": 2, "quality_attempts": 2},
    )
    patch = QualityNode(FixtureResearchModel(), ResearchOptions()).failure(
        state, "critic", ModelUnavailable("opaque failure")
    )
    usage = usage_summary(apply_update(state, patch), provider_usage=receipts())
    assert usage["model_requests_blocked_locally"] == 0
    assert usage["token_usage_unknown_records"] == 1


def test_gemini_token_guard_creates_no_receipt_or_http_request(tmp_path):
    budget = BudgetLimits(max_model_calls=6, max_total_tokens=100)
    model = GeminiResearchModel(
        "gemini-synthetic",
        SecretStr("synthetic-key"),
        budget,
        transport=httpx.MockTransport(lambda request: pytest.fail("Blocked request reached HTTP")),
    )
    model.bind_run(tmp_path, "local", "run_test", budget, existing=False)
    with pytest.raises(ModelBudgetExceeded) as failure:
        asyncio.run(
            model.plan(ResearchRequest(question="Synthetic AI engineering"), max_questions=1)
        )
    assert failure.value.reason == "token_limit"
    assert model.observations == []
    assert model.usage()["paid_calls"] == 0
    assert model._ledger.records() == []


def test_ledger_call_limit_and_failed_reservation_are_preserved(tmp_path):
    budget = BudgetLimits(max_model_calls=3)
    ledger = ModelCallLedger(tmp_path, "local", "run_test", "synthetic-model", budget)
    for i in range(3):
        row, _ = ledger.reserve(str(i), {"reserved_tokens": 100})
        ledger.finish(row.model_copy(update={"status": "failed"}))
    before = ledger.records()
    with pytest.raises(ModelBudgetExceeded) as error:
        ledger.reserve("blocked", {"reserved_tokens": 100})
    assert error.value.reason == "model_call_limit"
    assert ledger.records() == before


def test_old_profile_restores_policy_three_and_omits_new_input_fields(tmp_path):
    service = ResearchService(tmp_path, options=ResearchOptions(production_policy_version=4))
    profile = json.dumps({"research_options": {"production_policy_version": 3}})
    service.restore_quality_profile(profile)
    assert service.options.production_policy_version == 3


def test_repeated_block_event_is_idempotent_for_usage():
    state = initial_state(ResearchRequest(question="Synthetic budget check"))
    first = blocked_model_patch(state, "critic", "token_limit", {})
    state = apply_update(state, first)
    second = blocked_model_patch(state, "critic", "token_limit", {})
    state = apply_update(state, second)
    assert sum(e["kind"] == "model_request_blocked" for e in state["events"].values()) == 1


def test_planner_token_block_is_exported_without_unknown_charge(tmp_path):
    budget = BudgetLimits(max_model_calls=6, max_total_tokens=100)
    model = GeminiResearchModel(
        "gemini-synthetic",
        SecretStr("synthetic-key"),
        budget,
        transport=httpx.MockTransport(lambda request: pytest.fail("No HTTP expected")),
    )
    service = ResearchService(
        tmp_path, model=model, options=ResearchOptions(production_policy_version=4)
    )
    state = asyncio.run(
        service.run(ResearchRequest(question="Compare solar and wind output."), budget)
    )
    assert state["stop_reason"] == "token_limit"
    summary = usage_summary(state, provider_usage=model.usage())
    assert summary["paid_model_calls"] == 0
    assert summary["model_requests_blocked_locally"] == 1
    assert summary["token_usage_unknown_records"] == 0


def test_legacy_critic_receipt_replays_under_saved_policy(tmp_path, monkeypatch):
    from test_model_resume import PLAN, adapter, reply

    from evidenceforge.planning import QueryGenerationRequest
    from evidenceforge.research import CoverageInput, SynthesisInput
    from evidenceforge.storage.checkpoints import CheckpointRepository

    fixture = FixtureResearchModel(plan_output=PLAN)
    seen = []
    budget = BudgetLimits(max_subquestions=1, max_model_calls=6)

    async def respond(request):
        payload = json.loads(request.content)
        title = payload["generationConfig"]["responseJsonSchema"]["title"]
        value = json.loads(payload["contents"][0]["parts"][0]["text"])
        seen.append(title)
        if title == "ReviewedPlanDraft":
            result = await fixture.plan(ResearchRequest.model_validate(value), max_questions=1)
            result["category"] = "research"
        elif title == "QueryBatchDraft":
            result = await fixture.generate_queries(QueryGenerationRequest.model_validate(value))
        elif title == "CoverageAssessment":
            result = await fixture.evaluate_coverage(CoverageInput.model_validate(value))
        elif title == "ReportDraft":
            result = await fixture.synthesize(SynthesisInput.model_validate(value))
        else:
            assert "request" not in value and "questions" not in value
            result = await fixture.critique(CriticInput.model_validate(value))
        return httpx.Response(200, json=reply(result))

    def service(policy):
        return ResearchService(
            tmp_path,
            model=adapter(respond, budget),
            options=ResearchOptions(production_policy_version=policy, quote_selection_version=0),
        )

    original = Critic.response

    async def interrupt_after_receipt(self, task, schema):
        await original(self, task, schema)
        raise RuntimeError("Synthetic interruption after saved critic receipt")

    with monkeypatch.context() as patch:
        patch.setattr(Critic, "response", interrupt_after_receipt)
        with pytest.raises(RuntimeError, match="saved critic receipt"):
            asyncio.run(
                service(3).run(
                    ResearchRequest(question="Compare solar and wind electricity output."), budget
                )
            )
    thread = CheckpointRepository(tmp_path / "checkpoints", "local").threads()[0]
    assert seen.count("CriticAssessment") == 1
    fresh = service(4)
    state = asyncio.run(fresh.resume(thread))
    assert state["run_status"] == "completed"
    assert fresh.options.production_policy_version == 3
    assert seen.count("CriticAssessment") == 1
    assert len(seen) == 5
