"""Offline integration gates for explicitly enabled mixed live-source workflows."""

import asyncio
import json

import httpx
import pytest

from evidenceforge.config import ConfigurationError
from evidenceforge.exports import report_export
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.nodes.approval import PlanDecision
from evidenceforge.planning import PlanDraft
from evidenceforge.reporting import render_report
from evidenceforge.research import ResearchOptions
from evidenceforge.research_demo import execute
from evidenceforge.retrieval.carbon_intensity import ENDPOINT, CarbonIntensityAdapter
from evidenceforge.retrieval.tavily import TavilyAdapter
from evidenceforge.schemas import ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService
from evidenceforge.storage.checkpoints import CheckpointFailure, CheckpointRepository
from evidenceforge.workbench import LocalWorkbench

PLAN = {
    "questions": [
        {"question": question, "acceptance_criteria": ["solar electricity"]}
        for question in (
            "What is solar electricity generation?",
            "Which factors affect solar electricity generation?",
            "How is solar electricity generation described?",
        )
    ]
}
OPTIONS = ResearchOptions(live_web=True, live_energy=True, require_plan_approval=True)


@pytest.fixture
def live_ports(monkeypatch):
    """Real adapters with mocked HTTP, retaining their checkpoint identities."""
    monkeypatch.setenv("EVIDENCEFORGE_TAVILY_API_KEY", "synthetic-test-search-key")
    clients, requests = [], []

    def respond(request):
        requests.append(request)
        if request.url.host == "api.tavily.com":
            assert request.method == "POST"
            assert str(request.url) == "https://api.tavily.com/search"
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Synthetic web source",
                            "url": "https://example.org/solar",
                            "raw_content": "Solar electricity generation depends on sunlight.",
                        }
                    ]
                },
            )
        assert str(request.url) == ENDPOINT and request.method == "GET"
        assert "authorization" not in request.headers
        shares = dict(
            gas=40, coal=0, biomass=5, nuclear=15, hydro=2, imports=10, other=1, wind=20, solar=7
        )
        return httpx.Response(
            200,
            json={
                "data": {
                    "from": "2026-01-01T12:00Z",
                    "to": "2026-01-01T12:30Z",
                    "generationmix": [
                        {"fuel": fuel, "perc": share} for fuel, share in shares.items()
                    ],
                }
            },
        )

    def client():
        result = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        clients.append(result)
        return result

    def web(key):
        adapter = TavilyAdapter(key, client())
        adapter._owned = True
        return adapter

    def energy():
        adapter = CarbonIntensityAdapter(client())
        adapter._owned = True
        return adapter

    monkeypatch.setattr("evidenceforge.services.research.TavilyAdapter", web)
    monkeypatch.setattr("evidenceforge.services.research.CarbonIntensityAdapter", energy)
    return clients, requests


def test_mixed_sources_approval_edit_resume_and_export(tmp_path, live_ports):
    clients, requests = live_ports

    def service():
        return ResearchService(
            tmp_path, model=FixtureResearchModel(plan_output=PLAN), options=OPTIONS
        )

    first = service()
    document = tmp_path / "solar.txt"
    document.write_text("Solar electricity generation uses photovoltaic panels.", encoding="utf-8")
    record = first.documents.ingest(document, "alice")
    request = ResearchRequest(
        question="Research solar electricity generation.",
        owner_scope="alice",
        document_ids=(record.id,),
    )
    paused = asyncio.run(first.run(request))
    assert paused["approval_status"] == "awaiting_approval"
    assert not requests and all(c.is_closed for c in clients)
    thread = paused["thread_id"]
    registration = CheckpointRepository(tmp_path / "checkpoints", "alice").load(thread)
    profile = json.loads(registration.profile)
    assert set(profile["adapters"]) == {"web", "api", "document"}
    assert profile["research_options"]["live_web"] is True
    assert profile["research_options"]["live_energy"] is True
    assert "synthetic-test-search-key" not in registration.profile

    edited = asyncio.run(service().edit_plan(thread, PlanDraft.model_validate(PLAN), 1, "alice"))
    assert edited["plan_version"] == 2
    assert not requests and all(c.is_closed for c in clients)
    with pytest.raises(CheckpointFailure, match="stale"):
        asyncio.run(service().edit_plan(thread, PlanDraft.model_validate(PLAN), 1, "alice"))
    assert all(c.is_closed for c in clients)

    completed = asyncio.run(
        service().resume(thread, "alice", decision=PlanDecision(approved=True, plan_version=2))
    )
    assert completed["run_status"] == "completed", completed["tool_errors"]
    assert {s["source_type"] for s in completed["source_records"].values()} == {
        "web",
        "api",
        "document",
    }
    assert len(requests) == 2 and all(c.is_closed for c in clients)
    assert all(a["support"] == "supported" for a in completed["citation_audit"])
    assert json.loads(report_export(completed))["evidence_mode"] == "live_sources_and_documents"
    assert "Live retrieval with offline fixture reasoning" in render_report(completed)
    assert "GB" in render_report(completed) or "Great Britain" in render_report(completed)

    replay = asyncio.run(service().resume(thread, "alice"))
    assert replay == completed
    assert len(requests) == 2 and all(c.is_closed for c in clients)
    mismatch = ResearchService(
        tmp_path,
        model=FixtureResearchModel(plan_output=PLAN),
        options=OPTIONS.model_copy(update={"live_energy": False}),
    )
    with pytest.raises(CheckpointFailure, match="configuration differs"):
        asyncio.run(mismatch.resume(thread, "alice"))
    assert len(requests) == 2 and all(c.is_closed for c in clients)
    with pytest.raises(CheckpointFailure):
        asyncio.run(service().resume(thread, "bob"))
    assert len(requests) == 2


def test_missing_key_fails_before_planning_and_workbench_submission(tmp_path):
    model = FixtureResearchModel()
    service = ResearchService(tmp_path, model=model, options=OPTIONS)
    request = ResearchRequest(question="Research solar electricity generation.")
    with pytest.raises(ConfigurationError, match="EVIDENCEFORGE_TAVILY_API_KEY"):
        asyncio.run(service.run(request))
    assert model.plan_calls == 0
    assert not list((tmp_path / "checkpoints").glob("*.sqlite*"))
    workbench = LocalWorkbench(tmp_path)
    try:
        with pytest.raises(ConfigurationError, match="EVIDENCEFORGE_TAVILY_API_KEY"):
            workbench.start(request, live_web=True)
        assert not workbench.jobs
    finally:
        workbench.executor.shutdown()


def test_injected_live_web_requires_matching_option(tmp_path):
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(503)))
    from pydantic import SecretStr

    adapter = TavilyAdapter(SecretStr("synthetic-test-key"), client)
    retrieval = RetrievalService(tmp_path, {SourceType.WEB: adapter})
    try:
        for options in (ResearchOptions(), ResearchOptions(live_energy=True)):
            with pytest.raises(ValueError, match="explicit matching"):
                ResearchService(tmp_path, retrieval=retrieval, options=options)
    finally:
        asyncio.run(client.aclose())


def test_offline_cli_cannot_enable_or_resume_live_sources(tmp_path, live_ports):
    clients, requests = live_ports
    with pytest.raises(ConfigurationError, match="cannot be combined"):
        asyncio.run(
            execute("Research solar electricity.", tmp_path, None, live_energy=True, offline=True)
        )
    state = asyncio.run(
        ResearchService(tmp_path, options=OPTIONS).run(
            ResearchRequest(question="Research solar electricity generation.")
        )
    )
    with pytest.raises(ConfigurationError, match="cannot resume with --offline"):
        asyncio.run(execute(None, tmp_path, None, resume=state["thread_id"], offline=True))
    assert not requests and all(c.is_closed for c in clients)


def test_default_profile_remains_compatible_without_live_flags(tmp_path):
    service = ResearchService(tmp_path)
    profile = json.loads(
        service.profile(
            service.retrieval_for(
                ResearchRequest(question="Research solar electricity generation.")
            )
        )
    )
    assert "live_web" not in profile["research_options"]
    assert "live_energy" not in profile["research_options"]


def test_web_failure_keeps_document_and_api_evidence(tmp_path, live_ports, monkeypatch):
    from evidenceforge.schemas import BudgetLimits

    clients, requests = live_ports

    def fail(request):
        requests.append(request)
        return httpx.Response(503)

    def web(key):
        client = httpx.AsyncClient(transport=httpx.MockTransport(fail))
        clients.append(client)
        adapter = TavilyAdapter(key, client)
        adapter._owned = True
        return adapter

    monkeypatch.setattr("evidenceforge.services.research.TavilyAdapter", web)
    service = ResearchService(
        tmp_path,
        model=FixtureResearchModel(plan_output=PLAN),
        options=ResearchOptions(live_web=True, live_energy=True),
    )
    document = tmp_path / "solar.txt"
    document.write_text("Solar electricity generation uses photovoltaic panels.", encoding="utf-8")
    record = service.documents.ingest(document, "alice")
    state = asyncio.run(
        service.run(
            ResearchRequest(
                question="Research solar electricity generation.",
                owner_scope="alice",
                document_ids=(record.id,),
            ),
            BudgetLimits(max_research_passes=1),
        )
    )
    assert state["run_status"] == "partial"
    assert state["stop_reason"] == "pass_limit"
    assert {s["source_type"] for s in state["source_records"].values()} == {"api", "document"}
    assert state["report_claims"] and state["gaps"]
    assert any(error["category"] == "provider" for error in state["tool_errors"].values())
    assert len(requests) == 2 and all(c.is_closed for c in clients)


def test_cancelled_mixed_source_plan_makes_no_search_calls(tmp_path, live_ports):
    clients, requests = live_ports
    service = ResearchService(tmp_path, options=OPTIONS)
    paused = asyncio.run(service.run(ResearchRequest(question="Research solar electricity.")))
    service.cancel(paused["thread_id"])
    cancelled = asyncio.run(ResearchService(tmp_path, options=OPTIONS).resume(paused["thread_id"]))
    assert cancelled["run_status"] == "cancelled"
    assert not requests and all(c.is_closed for c in clients)
