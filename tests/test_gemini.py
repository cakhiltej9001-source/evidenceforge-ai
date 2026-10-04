"""Gemini transport, redaction, budgets and graph integration without network access."""

import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.planning import ModelUnavailable, QueryGenerationRequest
from evidenceforge.reporting import render_report
from evidenceforge.research import CoverageInput, CriticInput, SynthesisInput
from evidenceforge.schemas import BudgetLimits, ResearchRequest
from evidenceforge.services.research import ResearchService
from evidenceforge.storage.checkpoints import CheckpointFailure

SECRET = "synthetic-gemini-test-secret"
QUESTION = "Compare solar and wind electricity output."


def reply(value, **extra):
    return {
        "candidates": [
            {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(value)}]}}
        ],
        "usageMetadata": {"promptTokenCount": 20, "totalTokenCount": 80},
        **extra,
    }


def model(handler, budget=None):
    return GeminiResearchModel(
        "gemini-3.8-flash",
        SecretStr(SECRET),
        budget or BudgetLimits(),
        transport=httpx.MockTransport(handler),
    )


PLAN = {
    "questions": [
        {"question": "What determines solar output?", "acceptance_criteria": ["solar output"]}
    ]
}


def test_transport_has_fixed_host_header_auth_and_structured_schema():
    seen = []

    def handler(request):
        seen.append(request)
        assert request.url.host == "generativelanguage.googleapis.com"
        assert SECRET not in str(request.url)
        assert request.headers["x-goog-api-key"] == SECRET
        data = json.loads(request.content)
        assert SECRET not in request.content.decode()
        assert data["generationConfig"]["responseJsonSchema"]["title"] == "PlanDraft"
        assert "tools" not in data
        assert data["generationConfig"]["maxOutputTokens"] == 4096
        return httpx.Response(200, json=reply(PLAN))

    adapter = model(handler)
    result = asyncio.run(adapter.plan(ResearchRequest(question=QUESTION), max_questions=2))
    assert result["questions"][0]["question"] == PLAN["questions"][0]["question"]
    assert len(seen) == 1
    assert adapter.observations[0]["total_tokens"] == 80
    assert SECRET not in json.dumps(adapter.observations)
    assert SECRET not in repr(adapter)


@pytest.mark.parametrize("status", [302, 400, 401, 403, 429, 500])
def test_provider_errors_never_echo_response_or_retry(status):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            status,
            json={"error": {"message": SECRET}},
            headers={"Location": "https://example.org/leak"},
        )

    adapter = model(handler)
    with pytest.raises(ModelUnavailable) as error:
        asyncio.run(adapter.plan(ResearchRequest(question=QUESTION), max_questions=2))
    assert SECRET not in str(error.value)
    assert len(seen) == 1
    assert adapter.observations[0]["total_tokens"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        reply({"questions": []}),
        reply(PLAN, candidates=[{"finishReason": "MAX_TOKENS", "content": {"parts": []}}]),
        reply(
            PLAN,
            candidates=[{"finishReason": "STOP", "content": {"parts": [{"text": "bad json"}]}}],
        ),
    ],
)
def test_incomplete_or_malformed_output_fails_closed(payload):
    adapter = model(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(ModelUnavailable):
        asyncio.run(adapter.plan(ResearchRequest(question=QUESTION), max_questions=2))


def test_response_size_is_bounded():
    adapter = model(lambda request: httpx.Response(200, content=b"x" * 1_000_001))
    with pytest.raises(ModelUnavailable):
        asyncio.run(adapter.plan(ResearchRequest(question=QUESTION), max_questions=2))


def test_call_limit_and_unknown_token_reservations_survive_failures():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(500, json={"message": SECRET})

    adapter = model(handler, BudgetLimits(max_model_calls=3))
    for _ in range(4):
        with pytest.raises(ModelUnavailable):
            asyncio.run(adapter.plan(ResearchRequest(question=QUESTION), max_questions=2))
    assert len(seen) == 3
    assert all(item["total_tokens"] is None for item in adapter.observations)

    small = model(handler, BudgetLimits(max_total_tokens=4096))
    with pytest.raises(ModelUnavailable):
        asyncio.run(small.plan(ResearchRequest(question=QUESTION), max_questions=2))
    assert not small.observations


def test_model_path_and_unenforceable_dollar_cap_are_rejected():
    for name in ["../redirect", "model?key=bad", "https://example.org"]:
        with pytest.raises(ValueError):
            GeminiResearchModel(name, SecretStr(SECRET), BudgetLimits())
    with pytest.raises(ValueError):
        GeminiResearchModel("gemini-3.8-flash", SecretStr(SECRET), BudgetLimits(max_cost_usd=1))


def test_full_graph_uses_gemini_transport_and_labels_fixture_evidence(tmp_path):
    fixtures = FixtureResearchModel()

    async def handler(request):
        data = json.loads(request.content)
        value = json.loads(data["contents"][0]["parts"][0]["text"])
        title = data["generationConfig"]["responseJsonSchema"]["title"]
        if title == "PlanDraft":
            result = await fixtures.plan(ResearchRequest.model_validate(value), max_questions=8)
        elif title == "QueryBatchDraft":
            result = await fixtures.generate_queries(QueryGenerationRequest.model_validate(value))
        elif title == "CoverageAssessment":
            result = await fixtures.evaluate_coverage(CoverageInput.model_validate(value))
        elif title == "ReportDraft":
            result = await fixtures.synthesize(SynthesisInput.model_validate(value))
        elif title == "CriticAssessment":
            result = await fixtures.critique(CriticInput.model_validate(value))
        else:
            raise AssertionError(title)
        return httpx.Response(200, json=reply(result))

    adapter = model(handler)
    service = ResearchService(tmp_path, model=adapter)
    state = asyncio.run(service.run(ResearchRequest(question=QUESTION)))
    assert state["run_status"] == "completed"
    markdown = render_report(state)
    assert "Live Gemini reasoning" in markdown
    assert "synthetic fixtures" in markdown
    assert "Offline synthetic" not in markdown
    assert len(adapter.observations) == 5
    assert service.report_path(state).read_text(encoding="utf-8") == markdown
    saved = json.loads(service.report_path(state).with_name("model_usage.json").read_text())
    assert len(saved["attempts"]) == 5
    assert saved["estimated_cost_usd"] is None
    assert SECRET not in json.dumps(state)
    assert SECRET not in json.dumps(saved)
    assert asyncio.run(service.resume(state["thread_id"])) == state
    with pytest.raises(CheckpointFailure, match="fresh model"):
        asyncio.run(service.run(ResearchRequest(question=QUESTION)))
    assert len(adapter.observations) == 5


def test_generation_failure_delivers_sanitized_failed_report(tmp_path):
    adapter = model(lambda request: httpx.Response(429, json={"error": {"message": SECRET}}))
    service = ResearchService(tmp_path, model=adapter)
    state = asyncio.run(service.run(ResearchRequest(question=QUESTION)))
    assert state["run_status"] == "failed"
    assert not state["final_report"]
    assert len(adapter.observations) == 1
    assert adapter.observations[0]["status"] == "http_429"
    assert SECRET not in service.report_path(state).read_text(encoding="utf-8")
    assert SECRET not in json.dumps(state)


def test_live_run_binds_service_token_allowance_before_request(tmp_path):
    adapter = model(lambda request: pytest.fail("No HTTP request within small token allowance"))
    service = ResearchService(tmp_path, model=adapter)
    state = asyncio.run(
        service.run(ResearchRequest(question=QUESTION), BudgetLimits(max_total_tokens=4096))
    )
    assert state["run_status"] == "failed"
    assert not adapter.observations


def test_configured_gemini_needs_explicit_evidence_and_owned_resume(tmp_path, monkeypatch):
    from evidenceforge.config import ConfigurationError, Settings
    from evidenceforge.research_demo import execute

    settings = Settings(
        model_provider="gemini", model_id="gemini-3.8-flash", model_api_key=SecretStr(SECRET)
    )
    monkeypatch.setattr("evidenceforge.research_demo.load_settings", lambda: settings)
    with pytest.raises(ConfigurationError, match="Live web retrieval"):
        asyncio.run(execute(QUESTION, tmp_path, None))
    with pytest.raises(CheckpointFailure, match="unavailable"):
        asyncio.run(execute(None, tmp_path, None, resume="thread_fake"))
