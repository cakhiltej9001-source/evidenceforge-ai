"""Failure diagnostics are useful, scoped and never replay failed paid requests."""

import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from evidenceforge.config import Settings
from evidenceforge.exports import report_export
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.schemas import BudgetLimits, ResearchRequest
from evidenceforge.services.failures import model_failures, public_failures
from evidenceforge.services.observability import public_timeline
from evidenceforge.services.research import ResearchService
from evidenceforge.storage.checkpoints import CheckpointFailure
from evidenceforge.storage.model_calls import ModelReceipt
from evidenceforge.workbench import LocalWorkbench


def test_failure_projection_uses_fixed_labels_not_provider_text():
    receipt = ModelReceipt(
        id="private-request-hash",
        status="failed",
        observation={
            "role": "input_guardrail",
            "status": "http_503",
            "secret": "PRIVATE_CANARY",
            "validation_errors": [],
        },
    )
    result = model_failures([receipt])
    assert result[0]["stage"] == "Question review"
    assert result[0]["http_status"] == 503
    assert "temporarily unavailable" in result[0]["message"]
    assert "PRIVATE" not in json.dumps(result)
    assert "private-request-hash" not in json.dumps(result)
    for code, message in [(401, "credentials"), (429, "quota"), (400, "settings")]:
        receipt.observation["status"] = f"http_{code}"
        assert message in model_failures([receipt])[0]["message"]
    receipt.observation["role"] = "PRIVATE_CANARY"
    receipt.observation["status"] = "http_PRIVATE_CANARY"
    assert "PRIVATE" not in json.dumps(model_failures([receipt]))
    receipt = receipt.model_copy(update={"status": "pending"})
    assert "unconfirmed" in model_failures([receipt])[0]["message"]


def test_failed_question_review_exports_actionable_fixed_errors(tmp_path):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(503, json={"error": {"message": "PRIVATE_CANARY"}})

    adapter = GeminiResearchModel(
        "synthetic-model",
        SecretStr("PRIVATE_KEY"),
        BudgetLimits(),
        transport=httpx.MockTransport(respond),
    )
    from evidenceforge.research import ResearchOptions

    service = ResearchService(
        tmp_path, model=adapter, options=ResearchOptions(production_policy_version=1)
    )
    state = asyncio.run(service.run(ResearchRequest(question="what is rose ?")))
    assert state["run_status"] == "failed" and not state["calls"]
    state["tool_errors"][next(iter(state["tool_errors"]))]["message"] = "PRIVATE_CANARY"
    exported = json.loads(report_export(state))
    assert exported["tool_errors"] == public_failures(state)
    assert exported["tool_errors"][0]["stage"] == "Question review"
    assert "PRIVATE_CANARY" not in json.dumps(exported)
    assert any(row["step"] == "Question review unavailable" for row in public_timeline(state))
    assert len(calls) == 1


def test_explicit_retry_is_new_owned_run_and_preserves_failure(tmp_path, monkeypatch):
    settings = Settings(
        model_provider="gemini", model_id="synthetic-model", model_api_key=SecretStr("test-key")
    )
    monkeypatch.setattr("evidenceforge.workbench.load_settings", lambda: settings)
    requests = []

    def reject(request):
        requests.append(request)
        return httpx.Response(503)

    real_model = GeminiResearchModel
    monkeypatch.setattr(
        "evidenceforge.workbench.GeminiResearchModel",
        lambda name, key, budget: real_model(
            name, key, budget, transport=httpx.MockTransport(reject)
        ),
    )
    app = LocalWorkbench(tmp_path)
    try:
        key = app.start(
            ResearchRequest(question="what is rose ?", owner_scope="alice"), gemini=True
        )
        first = app.jobs[("alice", key)].result(timeout=60)
        assert app.model_failures("alice", first["thread_id"])[0]["http_status"] == 503
        exported = json.loads(app.export("alice", first["thread_id"]))
        assert exported["provider_failures"][0]["http_status"] == 503
        with pytest.raises(CheckpointFailure):
            app.model_failures("bob", first["thread_id"])
        with pytest.raises(CheckpointFailure):
            app.retry("bob", first["thread_id"])
        assert len(requests) == 1
        key = app.retry("alice", first["thread_id"])
        second = app.jobs[("alice", key)].result(timeout=60)
        assert second["run_id"] != first["run_id"]
        assert second["budget"] == first["budget"]
        assert second["request"] == first["request"]
        assert app.snapshot("alice", first["thread_id"]) == first
        assert app.paid_usage("alice", first["thread_id"])["paid_calls"] == 1
        assert app.paid_usage("alice", second["thread_id"])["paid_calls"] == 1
        assert len(requests) == 2
        app.snapshot("alice", second["thread_id"])
        assert len(requests) == 2
    finally:
        app.close()


def test_timeout_diagnostic_is_recorded_without_retry():
    calls = []

    def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout("PRIVATE_CANARY")

    model = GeminiResearchModel(
        "synthetic-model",
        SecretStr("test-key"),
        BudgetLimits(),
        transport=httpx.MockTransport(timeout),
    )
    from evidenceforge.planning import ModelUnavailable

    with pytest.raises(ModelUnavailable):
        asyncio.run(model.plan(ResearchRequest(question="what is rose ?"), max_questions=1))
    assert model.observations[0]["status"] == "timeout"
    assert len(calls) == 1
    assert "PRIVATE_CANARY" not in json.dumps(model.observations)


@pytest.mark.parametrize("source_only", [False, True])
def test_ui_retry_recovers_a_rose_answer_with_mocked_providers(tmp_path, monkeypatch, source_only):
    from pathlib import Path

    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    from evidenceforge import ui
    from evidenceforge.models.research import FixtureResearchModel
    from evidenceforge.planning import QueryGenerationRequest
    from evidenceforge.research import CoverageInput, CriticInput
    from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievedSource
    from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
    from evidenceforge.schemas import SourceType
    from evidenceforge.services.retrieval import RetrievalService

    budget = BudgetLimits(
        max_model_calls=6,
        max_subquestions=1,
        max_queries_per_pass=1,
        max_research_passes=1,
        max_searches=1,
        max_rewrites=0,
    )
    settings = Settings(
        data_dir=tmp_path,
        model_provider="gemini",
        model_id="synthetic-model",
        model_api_key=SecretStr("test-key"),
        tavily_api_key=SecretStr("test-search-key"),
        budget=budget,
    )
    for key, value in {
        "MODEL_PROVIDER": "gemini",
        "MODEL_ID": "synthetic-model",
        "MODEL_API_KEY": "test-key",
        "TAVILY_API_KEY": "test-search-key",
        "DATA_DIR": str(tmp_path),
        "BUDGET": budget.model_dump_json(),
    }.items():
        monkeypatch.setenv("EVIDENCEFORGE_" + key, value)
    monkeypatch.setattr(ui, "load_settings", lambda: settings)
    monkeypatch.setattr("evidenceforge.workbench.load_settings", lambda: settings)
    requests = []
    fixture = FixtureResearchModel()

    async def respond(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(503, json={"error": {"message": "PRIVATE_CANARY"}})
        payload = json.loads(request.content)
        title = payload["generationConfig"]["responseJsonSchema"]["title"]
        value = json.loads(payload["contents"][0]["parts"][0]["text"])
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

    original_service = LocalWorkbench.service

    class SimulatedLiveSearch(FixtureRetrievalAdapter):
        is_live = True

    def service(self, *args, **kwargs):
        instance = original_service(self, *args, **kwargs)
        instance.model._transport = httpx.MockTransport(respond)
        instance.retrieval = RetrievalService(
            self.data_dir,
            {
                SourceType.WEB: SimulatedLiveSearch(
                    RetrievalBatch(
                        results=(
                            RetrievedSource(
                                title="Synthetic rose fixture",
                                url="https://example.org/rose",
                                content=(
                                    "Synthetic fixture: a rose is a flowering plant "
                                    "in the genus Rosa."
                                ),
                            ),
                        )
                    )
                )
            },
        )
        return instance

    monkeypatch.setattr(LocalWorkbench, "service", service)
    original_submit = LocalWorkbench.submit
    apps = []

    def submit(self, owner, key, operation):
        apps.append(self)
        result = original_submit(self, owner, key, operation)
        self.jobs[(owner, key)].result(timeout=90)
        return result

    monkeypatch.setattr(LocalWorkbench, "submit", submit)
    at = AppTest.from_file(Path(ui.__file__), default_timeout=90)
    try:
        at.run()
        next(t for t in at.text_area if t.label == "Research question").set_value("what is rose ?")
        next(b for b in at.button if b.label == "Create plan").click().run()
        at.run()
        assert not at.exception
        assert any("Question review (HTTP 503)" in e.value for e in at.error), (
            [e.value for e in at.error],
            [m.value for m in at.info],
            len(requests),
            list(at.session_state.filtered_state),
        )
        first_thread = at.session_state["selected_thread"]
        label = (
            "Get source quotations without Gemini"
            if source_only
            else "Try again with a new Gemini plan"
        )
        next(b for b in at.button if b.label == label).click().run()
        at.run()
        assert not at.exception and not at.error
        next(b for b in at.button if b.label == "Approve plan").click().run()
        at.run()
        assert not at.exception and not at.error
        final = apps[0].snapshot("local", at.session_state["selected_thread"])
        assert final["run_status"] == "completed" and final["report_claims"]
        assert final["thread_id"] != first_thread
        assert apps[0].snapshot("local", first_thread)["run_status"] == "failed"
        assert len(requests) == (1 if source_only else 7)
        assert bool(apps[0].paid_usage("local", final["thread_id"])) is not source_only
        assert any("flowering plant" in m.value for m in at.markdown)
    finally:
        for app in apps:
            app.close()
