"""Regressions for the live-report failure: usable answers and receipt-backed totals."""

import asyncio
import json
from copy import deepcopy
from datetime import date

import pytest

from evidenceforge.answering import answer_excerpts, unresolved_answer
from evidenceforge.exports import report_export
from evidenceforge.graph.state import StateSnapshot, apply_update, initial_state
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.reporting import readable_quote, render_report
from evidenceforge.research import ResearchOptions
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import BudgetLimits, ReportSection, ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService
from evidenceforge.services.usage import PriceTable, usage_summary
from evidenceforge.storage.model_calls import ModelReceipt, model_usage


def business_report(root, passages, question="How to become an AI entrepreneur?"):
    model = FixtureResearchModel(
        plan_output={
            "questions": [
                {
                    "question": "How do I start an AI business?",
                    "acceptance_criteria": [
                        "AI business",
                        "business model types",
                        "technical infrastructure data",
                    ],
                }
            ]
        }
    )
    batch = RetrievalBatch(
        results=tuple(
            RetrievedSource(
                title=f"Synthetic business guide {i}",
                url=f"https://example.org/business-{i}",
                content=passage,
            )
            for i, passage in enumerate(passages)
        )
    )
    service = ResearchService(
        root,
        model=model,
        options=ResearchOptions(production_policy_version=3),
        retrieval=RetrievalService(root, {SourceType.WEB: FixtureRetrievalAdapter(batch)}),
    )
    state = asyncio.run(
        service.run(
            ResearchRequest(question=question),
            BudgetLimits(
                max_searches=1,
                max_research_passes=1,
                max_queries_per_pass=1,
                max_subquestions=1,
                max_model_calls=6,
                max_rewrites=0,
            ),
        )
    )
    assert state["final_report"] and state["report_claims"]
    return state


def answer(markdown):
    return markdown.split("## Answer\n\n", 1)[1].split("## Key Findings", 1)[0]


def test_plan_vocabulary_recovers_partial_how_to_answer_without_new_calls(tmp_path):
    passage = (
        "An AI business begins with interviews to identify a customer problem. "
        "Validate demand before building an AI business product."
    )
    state = business_report(tmp_path, [passage])
    before = json.dumps(state, sort_keys=True)
    snapshot = StateSnapshot.model_validate(state)
    excerpts = answer_excerpts(snapshot)
    assert excerpts
    for item in excerpts:
        retained = snapshot.evidence_store[item.evidence_id].passage
        assert retained[item.start_offset : item.end_offset] == item.text
    result = answer(render_report(state, answer_first=True, local_source_links=True))
    assert "customer problem" in result and "#saved-source-" in result
    assert "partial answer" in result and "Still unresolved" in result
    assert "business model types" in result and "technical infrastructure data" in result
    assert "research/search limit" in result
    assert state["run_status"] == "partial" and state["stop_reason"] == "pass_limit"
    assert json.dumps(state, sort_keys=True) == before
    assert len(state["calls"]) == 1  # Only the fixture search; no extra answer call.


def test_long_how_to_context_preserves_caution_instead_of_abstaining(tmp_path):
    passage = (
        "An AI business starts with a customer problem. "
        + "An AI business pilot needs interviews, measured feedback, and careful testing. " * 5
        + "However, this advice does not guarantee success."
    )
    assert 320 < len(passage) < 1000
    state = business_report(tmp_path, [passage])
    excerpts = answer_excerpts(StateSnapshot.model_validate(state))
    assert len(excerpts) == 1 and excerpts[0].text == passage
    assert readable_quote(passage) in answer(render_report(state, answer_first=True))


def test_tangential_and_promotional_quotes_do_not_fill_the_answer(tmp_path):
    useful = "An AI business begins by interviewing customers and testing demand."
    state = business_report(
        tmp_path,
        [
            useful,
            "AI product managers prioritize a backlog and coordinate engineering teams.",
            "An AI business can grow if you join my course and subscribe to my community.",
        ],
    )
    result = answer(render_report(state, answer_first=True))
    assert "interviewing customers" in result
    assert "product managers" not in result and "join my course" not in result


def test_how_many_facts_do_not_use_the_how_to_fallback(tmp_path):
    state = business_report(
        tmp_path,
        ["An AI business begins by testing customer demand."],
        question="How many AI startups exist in India?",
    )
    assert not answer_excerpts(StateSnapshot.model_validate(state))


def test_entities_are_readable_but_original_audit_text_is_preserved(tmp_path):
    passage = "An AI business founder&#x27;s first step is to validate a customer problem."
    state = business_report(tmp_path, [passage])
    original = deepcopy(state)
    rendered = render_report(state, answer_first=True)
    assert "&amp;#x27;" not in rendered
    assert readable_quote(passage) in rendered
    assert "Character entities are decoded" in rendered
    assert state == original
    assert any(e["passage"] == passage for e in state["evidence_store"].values())
    assert "<script>" not in readable_quote("&lt;script&gt;alert(1)&lt;/script&gt;")


def provider_counts(*, unknown=False):
    receipts = []
    for i in range(5):
        pending = unknown and i == 4
        receipts.append(
            ModelReceipt(
                id=f"receipt_{i}",
                status="pending" if pending else "succeeded",
                observation={
                    "model": "synthetic-model",
                    "reserved_tokens": 100,
                    "input_tokens": None if pending else 10,
                    "output_tokens_including_thinking": None if pending else 20,
                    "total_tokens": None if pending else 30,
                },
            )
        )
    return model_usage(receipts)


def usage_state():
    return apply_update(
        initial_state(ResearchRequest(question="Synthetic usage test")),
        {"planning_attempts": 2, "quality_attempts": 3},
    )


def test_durable_model_totals_replace_unknown_node_estimates_without_mutation():
    state = usage_state()
    original = deepcopy(state)
    assert usage_summary(state)["token_usage_unknown_records"] == 5
    result = usage_summary(state, provider_usage=provider_counts())
    assert result["input_tokens_known"] == 50 and result["output_tokens_known"] == 100
    assert result["token_usage_unknown_records"] == 0
    assert result["model_attempts"] == result["paid_model_calls"] == 5
    assert result["model_usage_source"] == "durable_gemini_receipts"
    assert result["estimated_cost_usd"] is None and result["cost_complete"] is False
    assert state == original


def test_pending_model_receipt_remains_unknown_and_conservatively_counted():
    result = usage_summary(usage_state(), provider_usage=provider_counts(unknown=True))
    assert result["input_tokens_known"] == 40 and result["output_tokens_known"] == 80
    assert result["token_usage_unknown_records"] == 1
    assert result["model_attempts"] == 5 and result["estimated_cost_usd"] is None


def test_missing_receipt_is_not_reported_as_known_usage():
    state = apply_update(usage_state(), {"quality_attempts": 4})
    result = usage_summary(state, provider_usage=provider_counts())
    assert result["model_attempts"] == 6 and result["token_usage_unknown_records"] == 1


def test_receipt_pricing_requires_dated_explicit_rates():
    prices = PriceTable(
        date(2026, 10, 17), {}, {"gemini:synthetic-model": 1.0}, {"gemini:synthetic-model": 2.0}
    )
    result = usage_summary(usage_state(), prices, provider_usage=provider_counts())
    assert result["estimated_cost_usd"] == pytest.approx(0.00025)
    assert result["cost_complete"] is True


def test_invalid_provider_counters_are_rejected():
    counts = provider_counts()
    counts["paid_calls"] = True
    with pytest.raises(ValueError):
        usage_summary(usage_state(), provider_usage=counts)


def test_report_json_uses_the_same_receipt_totals_as_the_ui(tmp_path):
    state = business_report(
        tmp_path,
        [
            "An AI business begins by interviewing customers and testing demand.",
        ],
    )
    data = json.loads(report_export(state, provider_usage=provider_counts()))
    assert data["usage"]["input_tokens_known"] == 50
    assert data["usage"]["token_usage_unknown_records"] == 0
    assert data["progress"]["run_status"] == "partial"


def test_plan_aware_disagreements_never_choose_one_how_to_source(tmp_path):
    state = business_report(
        tmp_path,
        [
            "An AI business pilot costs 100 dollars.",
            "An AI business pilot costs 200 dollars.",
        ],
    )
    snapshot = StateSnapshot.model_validate(state)
    report = snapshot.final_report
    report = report.model_copy(
        update={
            "sections": tuple(report.sections)
            + (ReportSection(name="disagreements", claim_ids=tuple(snapshot.report_claims)),),
        }
    )
    snapshot = snapshot.model_copy(update={"final_report": report, "draft_report": report})
    assert unresolved_answer(snapshot) and not answer_excerpts(snapshot)
    result = answer(render_report(snapshot.model_dump(mode="json"), answer_first=True))
    assert "single answer is not established" in result
    assert "100" not in result and "200" not in result


def test_coverage_backed_wording_keeps_whole_context_when_terms_differ(tmp_path):
    passage = "AI founders validate customers through interviews before investing in development."
    state = business_report(tmp_path, [passage])
    qid = state["research_questions"][0]["id"]
    eid = next(iter(state["evidence_store"]))
    state["coverage_by_question"][qid]["status"] = "partial"
    state["coverage_by_question"][qid]["evidence_ids"] = [eid]
    snapshot = StateSnapshot.model_validate(state)
    excerpts = answer_excerpts(snapshot)
    assert len(excerpts) == 1 and excerpts[0].text == passage
    assert readable_quote(passage) in answer(render_report(state, answer_first=True))


def test_partial_receipt_pricing_keeps_a_lower_bound_without_claiming_full_cost():
    prices = PriceTable(
        date(2026, 10, 17),
        {},
        {"gemini:synthetic-model": 1.0},
        {"gemini:synthetic-model": 2.0},
    )
    result = usage_summary(usage_state(), prices, provider_usage=provider_counts(unknown=True))
    assert result["estimated_cost_usd"] is None and result["cost_complete"] is False
    assert result["known_cost_lower_bound_usd"] == pytest.approx(0.0002)
