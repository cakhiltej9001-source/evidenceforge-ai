"""Submission regressions: clean evidence and a real bounded revision cycle."""

import asyncio
import json
from copy import deepcopy

import pytest

from evidenceforge.answering import answer_excerpts
from evidenceforge.graph.state import StateSnapshot
from evidenceforge.nodes.approval import PlanDecision
from evidenceforge.presentation import display_issues
from evidenceforge.reporting import render_report
from evidenceforge.research import CoverageAssessment, CoverageInput, ResearchOptions
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService

QUESTION = "How to become an AI engineer?"
CRITERIA = (
    "Education degrees certifications",
    "Programming languages frameworks",
    "Technical skills machine learning",
    "Practical portfolio projects",
)
PASSAGES = (
    "AI engineer education includes computer science degrees and relevant certifications.",
    "AI engineer programming languages include Python; useful frameworks include PyTorch.",
    "AI engineer technical skills include machine learning, statistics and model evaluation.",
    "AI engineer practical experience includes portfolio projects with tests and deployment.",
)
PROMO = (
    "Your journey includes programming mastery and real-world portfolio development. "
    "If you want a faster, structured path into AI engineering, consider the AI Software "
    "Engineers Bootcamp at WorkForce Institute. This program provides hands-on mentorship, "
    "real projects, and career preparation to help you transition confidently into the field."
)
PLAN = {"questions": [{"question": QUESTION, "acceptance_criteria": CRITERIA}]}


def sources(passages=(*PASSAGES, PROMO)):
    return FixtureRetrievalAdapter(
        RetrievalBatch(
            results=tuple(
                RetrievedSource(
                    title=f"Synthetic submission regression {i}",
                    url=f"https://example.org/regression/{i}",
                    content=text,
                )
                for i, text in enumerate(passages)
            )
        )
    )


@pytest.mark.parametrize(
    "pitch",
    [
        PROMO,
        "Example Academy's AI Bootcamp helps you become an AI engineer.",
        "The AI engineer course offers hands-on mentorship and career preparation.",
    ],
)
def test_third_party_training_pitch_cannot_be_highlighted(pitch):
    assert display_issues(pitch, year=2026, request=QUESTION)


def test_neutral_training_discussion_remains_eligible():
    assert not display_issues(
        "AI engineer education can include degrees, courses or bootcamps.",
        year=2026,
        request=QUESTION,
    )


def test_answer_covers_distinct_criteria_and_preserves_historical_records(tmp_path):
    from evidenceforge.models.research import FixtureResearchModel

    state = asyncio.run(
        ResearchService(
            tmp_path,
            model=FixtureResearchModel(plan_output=PLAN),
            retrieval=RetrievalService(tmp_path, {SourceType.WEB: sources()}),
        ).run(ResearchRequest(question=QUESTION), BudgetLimits(max_subquestions=1))
    )
    before = deepcopy(state)
    snapshot = StateSnapshot.model_validate(state)
    excerpts = answer_excerpts(snapshot)
    assert {item.criterion for item in excerpts} >= set(CRITERIA)
    assert all("Bootcamp" not in item.text for item in excerpts)
    for item in excerpts:
        evidence = snapshot.evidence_store[item.evidence_id]
        assert evidence.passage[item.start_offset : item.end_offset] == item.text
    markdown = render_report(state, answer_first=True)
    highlighted = markdown.split("## Sources", 1)[0]
    assert all(
        heading in highlighted
        for heading in (
            "Education and training",
            "Programming and tools",
            "Technical foundations",
            "Practical experience",
        )
    )
    assert "WorkForce" not in highlighted and "hands-on mentorship" not in highlighted
    assert "WorkForce" in render_report(state)
    assert state == before


@pytest.mark.parametrize(
    ("rewrite_limit", "always_revise", "expected_calls", "expected_status"),
    [(1, False, 6, "completed"), (0, False, 4, "partial"), (1, True, 6, "partial")],
)
def test_approval_resume_and_revision_stay_inside_six_calls(
    tmp_path, rewrite_limit, always_revise, expected_calls, expected_status
):
    from test_reviewed_planning import adapter, reply

    titles = []
    critic_calls = 0
    budget = BudgetLimits(
        max_model_calls=6,
        max_subquestions=1,
        max_queries_per_pass=1,
        max_searches=1,
        max_research_passes=1,
        max_rewrites=rewrite_limit,
    )
    search = sources()

    def respond(request):
        nonlocal critic_calls
        payload = json.loads(request.content)
        title = payload["generationConfig"]["responseJsonSchema"]["title"]
        titles.append(title)
        value = json.loads(payload["contents"][0]["parts"][0]["text"])
        if title == "ReviewedPlanDraft":
            result = {"category": "research", **PLAN}
        elif title == "CoverageSelectionDraft":
            assert all("Bootcamp" not in item["passage"] for item in value["evidence"])
            fields = payload["generationConfig"]["responseJsonSchema"]["$defs"]["CoverageMatch"]
            assert fields["properties"]["criterion_id"]["enum"] == ["c_0", "c_1", "c_2", "c_3"]
            assert "maxItems" not in json.dumps(payload["generationConfig"]["responseJsonSchema"])
            result = {
                "matches": [
                    {
                        "criterion_id": criterion["id"],
                        "evidence_ids": [
                            next(e["id"] for e in value["evidence"] if e["passage"] == PASSAGES[i])
                        ],
                    }
                    for i, criterion in enumerate(value["criteria"])
                ]
            }
        elif title == "QuoteSelectionDraft":
            assert "Third-party sales copy" in payload["systemInstruction"]["parts"][0]["text"]
            assert all("Bootcamp" not in e["passage"] for e in value["evidence"])
            result = {
                "claims": [
                    {
                        "evidence_id": e["id"],
                        "question_ids": e["question_ids"],
                        "section": "key_findings",
                    }
                    for e in value["evidence"]
                ]
            }
        elif title == "CriticAssessment":
            critic_calls += 1
            revise = critic_calls == 1 or always_revise
            result = {
                "decision": "revise" if revise else "approved",
                "revision_brief": ["Select the clearest supported portfolio guidance."]
                if revise
                else [],
            }
        else:
            pytest.fail("An extra query-generation call consumed revision capacity.")
        return reply(result)

    def service():
        return ResearchService(
            tmp_path,
            model=adapter(respond, budget),
            retrieval=RetrievalService(tmp_path, {SourceType.WEB: search}),
            options=ResearchOptions(
                production_policy_version=6,
                require_plan_approval=True,
                node_timeout_seconds=60,
            ),
        )

    paused = asyncio.run(service().run(ResearchRequest(question=QUESTION), budget))
    assert len(titles) == 1 and search.calls == 0
    assert paused["approval_status"] == "awaiting_approval"
    result = asyncio.run(
        service().resume(
            paused["thread_id"],
            decision=PlanDecision(approved=True, plan_version=paused["plan_version"]),
        )
    )
    assert result["run_status"] == expected_status
    assert len(titles) == expected_calls and search.calls == 1
    assert result["planning_attempts"] + result["quality_attempts"] == expected_calls
    assert result["revision_count"] == rewrite_limit
    assert result["draft_report"]["draft_version"] == rewrite_limit + 1
    assert all(
        a["structural_valid"] and a["support"] == "supported" for a in result["citation_audit"]
    )
    assert any("Bootcamp" in e["passage"] for e in result["evidence_store"].values())
    assert all("Bootcamp" not in c["statement"] for c in result["report_claims"].values())
    assert result["budget"] == budget.model_dump(mode="json")
    assert any(
        "without a query-generation model call" in event["message"]
        for event in result["events"].values()
    )
    assert asyncio.run(service().resume(paused["thread_id"])) == result
    assert len(titles) == expected_calls and search.calls == 1


@pytest.mark.parametrize("invalid", [None, "unknown", "duplicate", "unlinked"])
def test_coverage_ids_map_to_exact_indices_and_reject_invalid_references(populated_state, invalid):
    from test_reviewed_planning import adapter, reply

    from evidenceforge.planning import ModelUnavailable

    snapshot = StateSnapshot.model_validate(populated_state)
    first = snapshot.research_questions[0].model_copy(
        update={"acceptance_criteria": ("Criterion zero", "Criterion one", "Criterion two")}
    )
    second = first.model_copy(update={"id": "q_other", "acceptance_criteria": ("Other",)})
    request_data = CoverageInput(
        questions=(first, second), evidence=tuple(snapshot.evidence_store.values())
    )

    def respond(request):
        data = json.loads(request.content)
        value = json.loads(data["contents"][0]["parts"][0]["text"])
        assert [c["id"] for c in value["criteria"]] == ["c_0", "c_1", "c_2", "c_3"]
        criterion = (
            "c_unknown" if invalid == "unknown" else "c_3" if invalid == "unlinked" else "c_2"
        )
        matches = [{"criterion_id": criterion, "evidence_ids": ["e_0"]}]
        if invalid == "duplicate":
            matches *= 2
        return reply({"matches": matches})

    model = adapter(respond, BudgetLimits())
    model.guidance_version = 3
    if invalid:
        with pytest.raises(ModelUnavailable):
            asyncio.run(model.evaluate_coverage(request_data))
    else:
        result = CoverageAssessment.model_validate(
            asyncio.run(model.evaluate_coverage(request_data))
        )
        assert result.questions[0].criteria[0].index == 2
        assert result.questions[0].criteria[0].evidence_ids == tuple(snapshot.evidence_store)
        assert result.questions[1].criteria == ()


def test_generic_ai_words_cannot_label_programming_as_mathematics(tmp_path):
    from evidenceforge.models.research import FixtureResearchModel

    math = "AI engineer mathematics includes statistics, linear algebra and probability."
    criteria = (
        "List core academic fields of study typically required for an AI engineer role.",
        "Specify key mathematical and statistical domains foundational to AI development.",
        "Identify essential programming languages and frameworks used in the industry.",
    )
    state = asyncio.run(
        ResearchService(
            tmp_path,
            model=FixtureResearchModel(
                plan_output={"questions": [{"question": QUESTION, "acceptance_criteria": criteria}]}
            ),
            retrieval=RetrievalService(
                tmp_path, {SourceType.WEB: sources((PASSAGES[1], math, PASSAGES[3]))}
            ),
        ).run(
            ResearchRequest(question=QUESTION),
            BudgetLimits(max_subquestions=1, max_research_passes=1),
        )
    )
    excerpts = answer_excerpts(StateSnapshot.model_validate(state))
    math_answer = next(e for e in excerpts if e.criterion == criteria[1])
    assert math_answer.text == math
    assert all(e.criterion != criteria[0] for e in excerpts)


@pytest.mark.parametrize("policy", [5, 6])
def test_approved_math_detail_survives_generic_topic_repetition(tmp_path, policy):
    from evidenceforge.models.research import FixtureResearchModel

    math = "Linear algebra and statistics support supervised models."
    text = "\n\n".join(
        [
            "AI engineer technical preparation includes generic planning topic "
            + str(i)
            + " and general career advice."
            for i in range(10)
        ]
        + [math]
    )
    state = asyncio.run(
        ResearchService(
            tmp_path,
            model=FixtureResearchModel(
                plan_output={
                    "questions": [
                        {
                            "question": "Describe AI engineer technical preparation.",
                            "acceptance_criteria": ["linear algebra statistics"],
                        }
                    ]
                }
            ),
            retrieval=RetrievalService(tmp_path, {SourceType.WEB: sources((text,))}),
            options=ResearchOptions(production_policy_version=policy),
        ).run(
            ResearchRequest(question=QUESTION),
            BudgetLimits(max_subquestions=1, max_research_passes=1),
        )
    )
    retained = [e["passage"] for e in state["evidence_store"].values()]
    assert (math in retained) is (policy == 6)
    assert len(retained) <= 8
