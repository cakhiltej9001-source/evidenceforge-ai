"""Criterion-specific passages survive bounded extraction without provider calls."""

import asyncio
from copy import deepcopy

import pytest

from evidenceforge.graph.state import StateSnapshot, apply_update
from evidenceforge.nodes.extraction import EvidenceExtractor
from evidenceforge.nodes.sources import SourceProcessor
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievalOptions, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.planning import PlanningService
from evidenceforge.services.retrieval import RetrievalService


@pytest.mark.parametrize(
    "criterion,distractor,proof",
    [
        (
            "Identify key mathematical concepts needed for understanding "
            "machine learning algorithms.",
            "AI engineer technical skills: data structures and algorithms support understanding "
            "machine learning algorithms, including decision trees and linked lists.",
            "Mathematics foundations include linear algebra and probability, needed for "
            "understanding predictions and Bayesian inference.",
        ),
        (
            "Identify key mathematical concepts needed for understanding "
            "machine learning algorithms.",
            "Common Mistakes: Beginners skip foundations in Python, mathematics, and "
            "classical machine learning, which makes advanced concepts harder to grasp.",
            "Calculus: Derivatives and gradients are the mathematical engine of learning. "
            "Optimization: Understanding gradient descent helps tune algorithms.",
        ),
        (
            "List core programming languages required for developing machine learning algorithms.",
            "AI engineer technical skills: developing machine learning algorithms requires "
            "algorithm evaluation, efficient processing, and testing.",
            "Programming languages for AI include Python and Java. These languages are used "
            "to build and deploy applications.",
        ),
    ],
)
def test_subject_evidence_beats_purpose_clause_overlap_under_passage_cap(
    tmp_path, criterion, distractor, proof
):
    request = ResearchRequest(question="What technical skills does an AI engineer need?")
    initial = asyncio.run(
        PlanningService().plan(
            request,
            BudgetLimits(max_subquestions=1, max_queries_per_pass=1, max_searches=1),
        )
    )
    # Keep the approved question identity and query association, changing only
    # this fixture's scope to the criterion whose evidence must survive.
    initial["research_questions"][0]["question"] = request.question
    initial["research_questions"][0]["acceptance_criteria"] = [criterion]
    content = distractor + "\n\n" + proof
    adapter = FixtureRetrievalAdapter(
        RetrievalBatch(
            results=(
                RetrievedSource(
                    title="Synthetic technical guide",
                    url="https://example.org/technical-guide",
                    content=content,
                ),
            )
        )
    )
    options = RetrievalOptions(max_passages_per_source=1)
    service = RetrievalService(tmp_path, {SourceType.WEB: adapter}, options)
    artifacts, ledger = service.components(initial)
    acquired = apply_update(
        initial,
        asyncio.run(SourceProcessor(service.adapters, artifacts, ledger, options)(initial)),
    )
    before = deepcopy(acquired)
    result = apply_update(
        acquired,
        EvidenceExtractor(
            artifacts,
            options,
            sentence_boundaries=True,
            criteria_focus=True,
        )(acquired),
    )
    assert acquired == before
    assert adapter.calls == 1
    evidence = StateSnapshot.model_validate(result).evidence_store
    assert len(evidence) == 1
    item = next(iter(evidence.values()))
    assert item.passage == proof
    assert content[item.locator.start_offset : item.locator.end_offset] == proof
    assert "evidence_limit" in {r["reason"] for r in result["rejected_evidence"].values()}
