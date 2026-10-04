"""Public energy adapter boundary, provenance and deployment launcher checks."""

import asyncio
import gzip
import json
import sys
from copy import deepcopy

import httpx
import pytest

from evidenceforge.energy_demo import execute
from evidenceforge.retrieval.carbon_intensity import ENDPOINT, CarbonIntensityAdapter
from evidenceforge.retrieval.contracts import RetrievalFailure, RetrievalOptions
from evidenceforge.schemas import (
    ArtifactReference,
    BudgetLimits,
    ResearchRequest,
    SearchQuery,
    SourceType,
)
from evidenceforge.services.planning import PlanningService
from evidenceforge.services.retrieval import RetrievalService
from evidenceforge.ui_launcher import main as launch

PAYLOAD = {
    "data": {
        "from": "2026-01-01T12:00Z",
        "to": "2026-01-01T12:30Z",
        "generationmix": [
            {"fuel": fuel, "perc": share}
            for fuel, share in dict(
                gas=40,
                coal=0,
                biomass=5,
                nuclear=15,
                hydro=2,
                imports=10,
                other=1,
                wind=20,
                solar=7,
            ).items()
        ],
    }
}
QUERY = SearchQuery(
    id="query_energy",
    question_ids=("question_energy",),
    text="solar wind https://localhost/private",
    source_type="web",
    research_pass=1,
)


def call(handler, options=None):
    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=True
        ) as client:
            return await CarbonIntensityAdapter(client).search(QUERY, options or RetrievalOptions())

    return asyncio.run(scenario())


def test_fixed_read_only_endpoint_and_provider_values():
    def handler(request):
        assert str(request.url) == ENDPOINT and request.method == "GET"
        assert not request.content and "authorization" not in request.headers
        return httpx.Response(200, json=PAYLOAD)

    batch = call(handler)
    source = batch.results[0]
    assert source.publisher == "National Energy System Operator"
    assert "solar electricity generation share was 7%" in source.content
    assert "wind electricity generation share was 20%" in source.content
    assert "Validated API payload:" in source.content and "not absolute" in source.content
    assert "Synthetic" not in source.content
    assert source.publication_date is None
    assert source.primary_evidence is None  # No unmeasured quality boost.
    assert batch.search_credits is None


def test_documented_single_item_array_and_compressed_response():
    raw = json.dumps({"data": [PAYLOAD["data"]]}).encode()
    batch = call(
        lambda request: httpx.Response(
            200,
            content=gzip.compress(raw),
            headers={"Content-Type": "application/json", "Content-Encoding": "gzip"},
        )
    )
    assert "7%" in batch.results[0].content


@pytest.mark.parametrize(
    "status, category",
    [(302, "provider"), (429, "rate_limit"), (503, "provider"), (403, "authentication")],
)
def test_status_errors_are_typed_and_redirects_never_followed(status, category):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(status, headers={"Location": "http://127.0.0.1/private"})

    with pytest.raises(RetrievalFailure) as error:
        call(handler)
    assert error.value.category == category and len(seen) == 1


@pytest.mark.parametrize(
    "kind",
    [
        "percentage",
        "boolean",
        "duplicate",
        "sum",
        "interval",
        "timezone",
        "extra",
        "empty",
        "array_many",
    ],
)
def test_invalid_provider_records_are_rejected(kind):
    payload = deepcopy(PAYLOAD)
    period = payload["data"]
    if kind == "percentage":
        period["generationmix"][0]["perc"] = 101
    elif kind == "boolean":
        period["generationmix"][0]["perc"] = True
    elif kind == "duplicate":
        period["generationmix"][0]["fuel"] = "solar"
    elif kind == "sum":
        period["generationmix"][0]["perc"] = 0
    elif kind == "interval":
        period["to"] = period["from"]
    elif kind == "timezone":
        period["from"] = "2026-01-01T12:00:00"
    elif kind == "extra":
        period["untrusted"] = "arbitrary provider text"
    elif kind == "empty":
        payload["data"] = []
    else:
        payload["data"] = [period, period]
    with pytest.raises(RetrievalFailure) as error:
        call(lambda request: httpx.Response(200, json=payload))
    assert error.value.category == "schema"


@pytest.mark.parametrize(
    "options", [RetrievalOptions(max_response_bytes=20), RetrievalOptions(max_source_bytes=20)]
)
def test_stream_and_source_size_limits(options):
    with pytest.raises(RetrievalFailure) as error:
        call(lambda request: httpx.Response(200, json=PAYLOAD), options)
    assert error.value.category == "schema"


def test_timeout_and_wrong_content_type_do_not_expose_response():
    def handler(request):
        raise httpx.ReadTimeout("private diagnostic", request=request)

    with pytest.raises(RetrievalFailure) as error:
        call(handler)
    assert error.value.category == "timeout" and "private" not in str(error.value)
    with pytest.raises(RetrievalFailure) as error:
        call(
            lambda request: httpx.Response(
                200, text="private HTML", headers={"Content-Type": "text/html"}
            )
        )
    assert error.value.category == "schema"


def test_service_retains_exact_spans_and_reuses_receipt_without_network(tmp_path):
    async def scenario():
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(200, json=PAYLOAD)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            retrieval = RetrievalService(tmp_path, {SourceType.WEB: CarbonIntensityAdapter(client)})
            planned = await PlanningService().plan(
                ResearchRequest(
                    question=(
                        "Compare solar and wind electricity generation shares in Great Britain."
                    )
                ),
                BudgetLimits(max_subquestions=1, max_queries_per_pass=1, max_searches=1),
            )
            first = await retrieval.retrieve(planned)
            second = await retrieval.retrieve(planned)
            assert len(seen) == 1 and first["evidence_store"] == second["evidence_store"]
            assert not first["tool_errors"] and first["evidence_store"]
            artifacts, _ = retrieval.components(first)
            for item in first["evidence_store"].values():
                locator = item["locator"]
                reference = ArtifactReference.model_validate(
                    first["raw_result_refs"][locator["snapshot_id"]]
                )
                text = artifacts.read(reference)
                assert text[locator["start_offset"] : locator["end_offset"]] == item["passage"]
            assert all(
                source["provider"] == "carbon_intensity"
                for source in first["source_records"].values()
            )

    asyncio.run(scenario())


def test_default_energy_source_is_synthetic_and_offline(tmp_path):
    state = asyncio.run(execute(tmp_path))
    assert not state["tool_errors"] and state["evidence_store"]
    assert all("Synthetic" in item["passage"] for item in state["evidence_store"].values())
    assert all(
        item["provider"] == "carbon_intensity_fixture" for item in state["source_records"].values()
    )


def test_launcher_defaults_local_and_explicit_container_port(monkeypatch):
    commands = []
    monkeypatch.setattr("evidenceforge.ui_launcher.importlib.util.find_spec", lambda name: object())
    monkeypatch.setattr(
        "evidenceforge.ui_launcher.subprocess.call", lambda cmd: commands.append(cmd) or 0
    )
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setattr(sys, "argv", ["evidenceforge-ui"])
    assert launch() == 0
    assert "--server.address=127.0.0.1" in commands[-1]
    assert "--server.port=8501" in commands[-1]
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setattr(sys, "argv", ["evidenceforge-ui", "--host", "0.0.0.0"])
    assert launch() == 0 and "--server.port=10000" in commands[-1]
    assert "--server.enableXsrfProtection=true" in commands[-1]
    monkeypatch.setenv("PORT", "99999")
    with pytest.raises(SystemExit):
        launch()
