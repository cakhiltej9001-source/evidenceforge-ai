"""Explicit enumerative criteria need retained concrete details, without network."""

import asyncio

import pytest

from evidenceforge.evidence.coverage_detail import enumerative_support
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.research import ResearchOptions
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService

MATH = "List essential mathematical and statistical foundations required for AI/ML roles."
GENERIC = (
    "Core skills include Python programming, mathematics and statistics, machine learning "
    "and deep learning, NLP, large language models, MLOps, and cloud platforms."
)
EXPLICIT = (
    "Mathematical and statistical foundations include linear algebra, probability, and calculus."
)


@pytest.mark.parametrize(
    "passage",
    [
        GENERIC,
        "Mathematical foundations matter. Programming foundations include Python, Java and R.",
        "Mathematics and statistics are essential. "
        "Programming languages include Python, Java and R.",
        "Mathematical and statistical foundations include mathematics and statistics.",
    ],
)
def test_parent_category_and_unrelated_neighbor_list_do_not_supply_members(passage):
    assert not enumerative_support(MATH, (passage,))


@pytest.mark.parametrize(
    "passage",
    [
        EXPLICIT,
        "Linear algebra, probability and calculus are mathematical foundations.",
        "Mathematical foundations: linear algebra; probability; calculus.",
        "Mathematical foundations include linear algebra. "
        "Statistical foundations include probability.",
        "Linear algebra, probability and calculus.",
    ],
)
def test_specific_foundation_enumerations_remain_eligible(passage):
    assert enumerative_support(MATH, (passage,))


def test_inventories_are_general_and_respect_explicit_count():
    criterion = "Describe three distinct portfolio project types that demonstrate applied skills."
    assert enumerative_support(
        criterion,
        (
            "Begin with practical exercises like predictive models, image recognition, chatbots, "
            "or recommendation engines.",
        ),
    )
    assert not enumerative_support(
        criterion, ("Portfolio projects include chatbots and recommendation engines.",)
    )
    assert enumerative_support(
        "List atmospheric gases.", ("The atmosphere contains nitrogen, oxygen and argon.",)
    )
    assert not enumerative_support(
        "List atmospheric gases.",
        ("The report includes atmospheric gases, temperatures and pressures.",),
    )
    assert enumerative_support("Identify the capital city.", ("Hyderabad.",))
    assert enumerative_support("linear algebra", ("linear algebra",))
    assert enumerative_support(
        "Explicitly list missing gas measurements.", ("Gas measurements are not reported.",)
    )


def test_generic_mentions_cannot_turn_current_workflow_sufficient(tmp_path):
    class OverconfidentModel(FixtureResearchModel):
        def __init__(self):
            super().__init__(
                plan_output={
                    "questions": [
                        {
                            "question": "Which foundations are required?",
                            "acceptance_criteria": ["Identify core programming languages.", MATH],
                        }
                    ]
                }
            )

        async def evaluate_coverage(self, request):
            ids = [item.id for item in request.evidence]
            return {
                "questions": [
                    {
                        "question_id": request.questions[0].id,
                        "criteria": [{"index": i, "evidence_ids": ids} for i in range(2)],
                    }
                ]
            }

    content = GENERIC + " Programming languages include Python, Java and R."
    batch = RetrievalBatch(
        results=(
            RetrievedSource(
                title="Synthetic skill evidence",
                url="https://example.org/skills",
                content=content,
            ),
        )
    )
    service = ResearchService(
        tmp_path,
        model=OverconfidentModel(),
        options=ResearchOptions(production_policy_version=6),
        retrieval=RetrievalService(tmp_path, {SourceType.WEB: FixtureRetrievalAdapter(batch)}),
    )
    state = asyncio.run(service.run(ResearchRequest(question="Which foundations are required?")))
    coverage = next(iter(state["coverage_by_question"].values()))
    assert coverage["status"] == "partial"
    assert "1 of 2 criteria" in coverage["rationale"]
    assert state["run_status"] == "partial"
    assert any("Concrete listed details" in gap["missing_aspect"] for gap in state["gaps"])
    assert any(GENERIC in item["passage"] for item in state["evidence_store"].values())
    assert not any("linear algebra" in item["passage"] for item in state["evidence_store"].values())
