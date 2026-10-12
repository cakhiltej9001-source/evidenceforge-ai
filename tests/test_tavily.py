"""Tavily HTTP contract tests use MockTransport; no credentials or remote requests."""

import asyncio
import json
import sys

import httpx
import pytest
from pydantic import SecretStr

from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievalFailure, RetrievalOptions
from evidenceforge.retrieval.tavily import TavilyAdapter
from evidenceforge.retrieval_demo import main
from evidenceforge.schemas import SearchQuery

QUERY = SearchQuery(
    id="query_a",
    question_ids=("question_a",),
    text="solar output",
    source_type="web",
    research_pass=1,
)
RESULT = {
    "title": "Public source",
    "url": "https://example.org/source",
    "content": "solar excerpt",
    "raw_content": "solar full text",
}


def call(handler, options=None):
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = TavilyAdapter(SecretStr("synthetic_key"), client)
            return await adapter.search(QUERY, options or RetrievalOptions())

    return asyncio.run(scenario())


def test_tavily_explicit_options_raw_content_credits_and_answer_excluded():
    seen = []

    def handler(request):
        seen.append(request)
        assert str(request.url) == "https://api.tavily.com/search"
        assert request.headers["Authorization"] == "Bearer synthetic_key"
        payload = json.loads(request.content)
        assert payload == {
            "query": "solar output",
            "search_depth": "basic",
            "topic": "general",
            "auto_parameters": False,
            "max_results": 5,
            "include_answer": False,
            "include_raw_content": "text",
            "include_images": False,
            "include_usage": True,
        }
        return httpx.Response(
            200,
            json={
                "results": [RESULT],
                "answer": "secret_generated_answer",
                "usage": {"credits": 1},
            },
        )

    batch = call(handler)
    assert isinstance(batch, RetrievalBatch) and len(seen) == 1
    assert batch.results[0].content == "solar full text"
    assert batch.results[0].content_scope == "full_text" and batch.search_credits == 1.0
    assert "secret_generated_answer" not in batch.model_dump_json()
    assert "synthetic_key" not in batch.model_dump_json()


@pytest.mark.parametrize("raw", [None, "", "  "])
def test_excerpt_fallback_is_labeled_and_unknown_credits_remain_null(raw):
    batch = call(
        lambda request: httpx.Response(
            200,
            json={
                "results": [{**RESULT, "raw_content": raw}],
            },
        )
    )
    assert batch.results[0].content == "solar excerpt"
    assert batch.results[0].content_scope == "search_excerpt"
    assert batch.search_credits is None


@pytest.mark.parametrize(
    "status,category",
    [
        (401, "authentication"),
        (403, "authentication"),
        (429, "rate_limit"),
        (500, "provider"),
        (302, "provider"),
    ],
)
def test_http_failures_are_fixed_and_no_retry_or_redirect(status, category):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status,
            text="private key and provider detail",
            headers={"Location": "https://another.example/private"},
        )

    with pytest.raises(RetrievalFailure) as caught:
        call(handler)
    assert caught.value.category == category and len(calls) == 1
    assert "private" not in str(caught.value)


@pytest.mark.parametrize(
    "payload",
    [
        {"answer": "unsupported answer without results"},
        {"results": "not a list"},
        {"results": [None]},
        {"results": [{**RESULT, "url": "https://user:password@example.org"}]},
        {"results": [{**RESULT, "url": "file:///private/document"}]},
        {"results": [{**RESULT, "raw_content": None, "content": None}]},
        {"results": [RESULT], "usage": {"credits": True}},
        {"results": [RESULT], "usage": {"credits": -1}},
    ],
)
def test_malformed_http_response_rejected_without_raw_data(payload):
    with pytest.raises(RetrievalFailure) as caught:
        call(lambda request: httpx.Response(200, json=payload))
    assert caught.value.category == "schema"
    assert str(caught.value) == "Retrieval operation failed."


def test_non_json_and_streamed_response_cap():
    with pytest.raises(RetrievalFailure) as caught:
        call(lambda request: httpx.Response(200, text="not JSON"))
    assert caught.value.category == "schema"
    with pytest.raises(RetrievalFailure) as caught:
        call(
            lambda request: httpx.Response(200, json={"results": [RESULT]}),
            RetrievalOptions(max_response_bytes=10),
        )
    assert caught.value.category == "schema"


def test_provider_result_count_bound():
    with pytest.raises(RetrievalFailure) as caught:
        call(
            lambda request: httpx.Response(200, json={"results": [RESULT, RESULT]}),
            RetrievalOptions(max_results=1),
        )
    assert caught.value.category == "schema"


@pytest.mark.parametrize(
    "exception,category",
    [
        (httpx.ReadTimeout("private_detail"), "timeout"),
        (httpx.ConnectError("private_detail"), "provider"),
    ],
)
def test_transport_failures_are_sanitized(exception, category):
    def handler(request):
        raise exception

    with pytest.raises(RetrievalFailure) as caught:
        call(handler)
    assert caught.value.category == category
    assert "private_detail" not in str(caught.value)


def test_offline_cli_and_missing_live_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evidenceforge-retrieve",
            "Compare solar and wind electricity output.",
            "--data-dir",
            str(tmp_path),
        ],
    )
    assert main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["execution_mode"] == "offline_fixture"
    assert output["research_passes_completed"] == 1
    assert output["evidence"] and output["report_generated"] is False
    assert output["run_status"] == "running"
    monkeypatch.setattr(sys, "argv", ["evidenceforge-retrieve", "solar output", "--live"])
    assert main() == 1
    assert "no search was made" in capsys.readouterr().out


def test_retry_after_rate_limit_is_bounded_and_does_not_expose_response():
    with pytest.raises(RetrievalFailure) as caught:
        call(
            lambda request: httpx.Response(
                429, headers={"Retry-After": "2"}, text="secret provider detail"
            )
        )
    assert caught.value.category == "rate_limit"
    assert caught.value.retry_after_seconds == 2.0
    assert "secret provider detail" not in str(caught.value)


@pytest.mark.parametrize("enabled", [False, True])
def test_site_operator_uses_structured_domain_filter_only_in_new_contract(enabled):
    seen = []
    query = QUERY.model_copy(update={"text": "site:nasa.gov Earth Mars atmosphere percentages"})

    def handler(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if enabled:
            assert payload["query"] == "Earth Mars atmosphere percentages"
            assert payload["include_domains"] == ["nasa.gov"]
        else:
            assert payload["query"] == query.text
            assert "include_domains" not in payload
        return httpx.Response(200, json={"results": [], "usage": {"credits": 1}})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = TavilyAdapter(SecretStr("synthetic_key"), client)
            return await adapter.search(query, RetrievalOptions(structured_domain_filters=enabled))

    asyncio.run(scenario())
    assert len(seen) == 1
