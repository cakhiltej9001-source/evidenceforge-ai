"""Regression checks for readable, exact quotations and constrained provider IDs."""

import asyncio
import json

import httpx
from pydantic import SecretStr

from evidenceforge.graph.state import StateSnapshot
from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.nodes.extraction import readable_spans, spans
from evidenceforge.reporting import escape, render_report
from evidenceforge.research import ResearchOptions, SynthesisInput
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService


def completed(root, version=3):
    batch = RetrievalBatch(
        results=(
            RetrievedSource(
                title="Synthetic Mars A",
                url="https://example.org/mars-a",
                content="Mars atmosphere contains 95 percent carbon dioxide.",
            ),
            RetrievedSource(
                title="Synthetic Mars B",
                url="https://example.net/mars-b",
                content="Mars atmosphere contains 95.9 percent carbon dioxide.",
            ),
        )
    )
    model = FixtureResearchModel(
        plan_output={
            "questions": [
                {
                    "question": "What is the carbon dioxide percentage in the Mars atmosphere?",
                    "acceptance_criteria": ["Mars atmosphere carbon dioxide percent"],
                }
            ]
        }
    )
    service = ResearchService(
        root,
        model=model,
        options=ResearchOptions(quote_selection_version=version),
        retrieval=RetrievalService(root, {SourceType.WEB: FixtureRetrievalAdapter(batch)}),
    )
    return asyncio.run(
        service.run(ResearchRequest(question="Compare the Mars atmosphere carbon dioxide percent."))
    )


def test_sentence_groups_preserve_decimals_words_and_exact_offsets():
    text = "Mars has 95.9 percent carbon dioxide. " + "Earth has nitrogen. " * 30
    found = list(readable_spans(text, 100))
    assert len(found) > 1
    assert all(text[a:b].endswith(".") and not text[a:b].startswith(" ") for a, b in found)
    assert " ".join(text[a:b] for a, b in found) == text.strip()
    assert all(b - a <= 100 for a, b in found)
    assert any("95.9" in text[a:b] for a, b in found)
    assert list(spans("abcdefghij", 4)) == [(0, 4), (4, 8), (8, 10)]


def test_oversized_sentence_is_never_silently_clipped():
    text = "One " + "longword " * 100 + "sentence."
    assert list(readable_spans(text, 100)) == [(0, len(text))]


def test_report_quotes_each_claim_once_and_qualifies_unresolved_percentages(tmp_path):
    state = completed(tmp_path)
    assert state["run_status"] == "completed"
    assert len(state["report_claims"]) == 2
    report = render_report(state)
    for claim in state["report_claims"].values():
        assert report.count(escape(claim["statement"])) == 1
    assert "Differing values remain unresolved" in report
    assert "Supported quotation Q" in report
    assert escape("95.9") in report and "95 percent" in report
    assert all(a["support"] == "supported" for a in state["citation_audit"])
    assert len(state["citation_audit"]) == len(state["report_claims"])


def test_legacy_report_contract_retains_original_presentation(tmp_path):
    state = completed(tmp_path, version=2)
    assert not any(e["kind"] == "readable_report" for e in state["events"].values())
    assert "Supported quotation Q" not in render_report(state)
    assert all(
        render_report(state).count(escape(c["statement"])) > 1
        for c in state["report_claims"].values()
    )


def test_provider_quote_schema_only_offers_real_evidence_and_question_ids(tmp_path):
    state = StateSnapshot.model_validate(completed(tmp_path))
    request = SynthesisInput(
        request=state.request,
        questions=state.research_questions,
        evidence=tuple(state.evidence_store.values()),
        gaps=(),
        revision_brief=(),
        draft_version=1,
    )
    captured = []

    def handler(http_request):
        data = json.loads(http_request.content)
        captured.append(data)
        fields = data["generationConfig"]["responseJsonSchema"]["$defs"]["QuoteSelection"][
            "properties"
        ]
        assert set(fields["evidence_id"]["enum"]) == {e.id for e in request.evidence}
        assert fields["question_ids"]["items"]["enum"] == [request.questions[0].id]
        result = {
            "claims": [
                {"evidence_id": request.evidence[0].id, "question_ids": [request.questions[0].id]}
            ]
        }
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(result)}]}}
                ]
            },
        )

    model = GeminiResearchModel(
        "test-model",
        SecretStr("synthetic-key"),
        BudgetLimits(),
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(model.select_quotes_constrained(request))
    assert result["claims"][0]["evidence_id"] == request.evidence[0].id
    assert len(captured) == 1


def test_compact_quote_aliases_restore_authentic_ids_without_mutating_input(tmp_path):
    state = StateSnapshot.model_validate(completed(tmp_path, version=4))
    request = SynthesisInput(
        request=state.request,
        questions=state.research_questions,
        evidence=tuple(state.evidence_store.values()),
        gaps=(),
        revision_brief=(),
        draft_version=1,
    )
    original = request.model_dump_json()

    def handler(http_request):
        payload = json.loads(http_request.content)
        value = json.loads(payload["contents"][0]["parts"][0]["text"])
        wire = payload["generationConfig"]["responseJsonSchema"]
        fields = wire["$defs"]["QuoteSelection"]["properties"]
        assert fields["evidence_id"]["enum"] == ["e_0", "e_1"]
        assert fields["question_ids"]["items"]["enum"] == ["q_0"]
        assert "maxItems" not in wire["properties"]["claims"]
        assert value["evidence"][0]["passage"] == request.evidence[0].passage
        result = {"claims": [{"evidence_id": "e_0", "question_ids": ["q_0"]}]}
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(result)}]}}
                ]
            },
        )

    model = GeminiResearchModel(
        "test-model",
        SecretStr("synthetic-key"),
        BudgetLimits(),
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(model.select_quotes_compact(request))
    assert result["claims"][0]["evidence_id"] == request.evidence[0].id
    assert result["claims"][0]["question_ids"] == [request.questions[0].id]
    assert request.model_dump_json() == original
