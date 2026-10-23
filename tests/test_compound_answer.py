"""Compound answer excerpts retain audit identity, exact offsets and qualifications."""

import asyncio
from copy import deepcopy

import pytest

from evidenceforge.answering import (
    answer_excerpts,
    bullet_heading_spans,
    criterion_fit,
    tool_facet_fit,
)
from evidenceforge.graph.state import StateSnapshot
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.research import ResearchOptions
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService

CRITERION = "List core programming languages and frameworks required for AI engineering roles."
LANGUAGE = (
    "Python is the primary language used across AI development, from data analysis "
    "to model building and deployment."
)
FRAMEWORK = (
    "AI engineering frameworks.\n"
    "Ideal when you need enterprise-grade deployment.\n"
    "\U0001f539 \U0001d5e3\U0001d606\U0001d5e7\U0001d5fc\U0001d5ff\U0001d5f0\U0001d5f5\n"
    "The go-to choice for research and rapid experimentation. "
    "Its dynamic computation graph makes prototyping and debugging easier.\n"
    "\U0001f539 Scikit-learn\n"
    "The backbone of classic machine learning. Perfect for tabular data and fast baselines."
)


def compound_report(root, passages):
    model = FixtureResearchModel(
        plan_output={
            "questions": [
                {"question": "How to become an AI engineer?", "acceptance_criteria": [CRITERION]}
            ]
        }
    )
    batch = RetrievalBatch(
        results=tuple(
            RetrievedSource(title=f"Synthetic {i}", url=f"https://example.org/{i}", content=text)
            for i, text in enumerate(passages)
        )
    )
    state = asyncio.run(
        ResearchService(
            root,
            model=model,
            options=ResearchOptions(quote_selection_version=3),
            retrieval=RetrievalService(root, {SourceType.WEB: FixtureRetrievalAdapter(batch)}),
        ).run(ResearchRequest(question="How to become an AI engineer?"))
    )
    # Presentation fixtures supply relevance links independently of the offline
    # model's simplistic coverage rubric; citation support remains unmodified.
    for coverage in state["coverage_by_question"].values():
        coverage["evidence_ids"] = list(state["evidence_store"])
    return state


@pytest.fixture
def paired_report(tmp_path):
    return compound_report(tmp_path, (LANGUAGE, FRAMEWORK))


def test_bullet_blocks_keep_exact_headings_bodies_and_exclude_orphan_intro():
    spans = list(bullet_heading_spans(FRAMEWORK))
    assert len(spans) == 2
    assert "Ideal when" not in FRAMEWORK[slice(*spans[0])]
    assert "Its dynamic" in FRAMEWORK[slice(*spans[0])]
    assert tool_facet_fit(FRAMEWORK[slice(*spans[0])], "frameworks") is not None
    assert list(bullet_heading_spans("Do not use every framework.\n" + FRAMEWORK)) == []


def test_pair_keeps_original_criterion_and_offsets_without_mutating_state(paired_report):
    before = deepcopy(paired_report)
    snapshot = StateSnapshot.model_validate(paired_report)
    excerpts = [item for item in answer_excerpts(snapshot) if item.criterion == CRITERION]
    assert {item.display_label for item in excerpts} == {
        "Programming languages",
        "Frameworks and libraries",
    }, (
        [c.statement for c in snapshot.report_claims.values()],
        [(a.claim_id, a.support) for a in snapshot.citation_audit],
        [(c.evidence_ids) for c in snapshot.coverage_by_question.values()],
        answer_excerpts(snapshot),
    )
    assert len(excerpts) == 2
    assert any(item.text == LANGUAGE for item in excerpts)
    for item in excerpts:
        assert (
            snapshot.evidence_store[item.evidence_id].passage[item.start_offset : item.end_offset]
            == item.text
        )
    assert paired_report == before


@pytest.mark.parametrize("missing", ["unaudited", "uncited"])
def test_one_eligible_facet_does_not_display_the_compound_criterion(paired_report, missing):
    state = deepcopy(paired_report)
    framework_ids = {
        cid for cid, claim in state["report_claims"].items() if "frameworks" in claim["statement"]
    }
    assert framework_ids
    if missing == "unaudited":
        state["citation_audit"] = [
            audit for audit in state["citation_audit"] if audit["claim_id"] not in framework_ids
        ]
    else:
        for section in state["final_report"]["sections"]:
            section["claim_ids"] = [cid for cid in section["claim_ids"] if cid not in framework_ids]
    excerpts = answer_excerpts(StateSnapshot.model_validate(state))
    assert not any(item.criterion == CRITERION for item in excerpts)


def test_general_compound_single_passage_fallback_is_preserved(tmp_path):
    text = (
        "AI engineering programming languages include R and Julia. "
        "AI engineering frameworks include tidymodels and Flux."
    )
    assert criterion_fit(CRITERION, text, "How to become an AI engineer?") is not None
    state = compound_report(tmp_path, (text,))
    excerpts = answer_excerpts(StateSnapshot.model_validate(state))
    assert any(item.criterion == CRITERION and item.text == text for item in excerpts)
    assert (
        criterion_fit(
            CRITERION, "Frameworks: PyTorch, TensorFlow.", "How to become an AI engineer?"
        )
        is None
    )


def test_punctuation_in_named_languages_and_explicit_counts():
    assert tool_facet_fit("Programming languages include C++ and C#.", "languages") is not None
    # A pair of single members must not silently meet an explicitly larger count.
    from evidenceforge.answering import compound_tools_criterion

    assert not compound_tools_criterion(
        "List three programming languages and two frameworks used in AI."
    )
