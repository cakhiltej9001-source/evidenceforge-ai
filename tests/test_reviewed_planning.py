"""Combined review preserves rejection, scope, approval and five-call budgets."""

import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from evidenceforge.models.gemini import GeminiResearchModel
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.nodes.approval import PlanDecision
from evidenceforge.planning import QueryGenerationRequest
from evidenceforge.research import CoverageInput, CriticInput, ResearchOptions
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService


def reply(result):
    return httpx.Response(
        200,
        json={
            "candidates": [
                {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(result)}]}}
            ],
            "usageMetadata": {"promptTokenCount": 20, "totalTokenCount": 80},
        },
    )


def adapter(handler, budget):
    return GeminiResearchModel(
        "gemini-3.1-flash-lite",
        SecretStr("test-key"),
        budget,
        transport=httpx.MockTransport(handler),
        request_timeout_seconds=45,
    )


@pytest.mark.parametrize("category", ["gibberish", "non_research", "manipulation", "vague"])
def test_combined_review_rejects_before_search(tmp_path, category):
    requests = []

    def respond(request):
        requests.append(request)
        return reply({"category": category, "questions": []})

    budget = BudgetLimits(max_model_calls=5)
    search = FixtureRetrievalAdapter()
    state = asyncio.run(
        ResearchService(
            tmp_path,
            model=adapter(respond, budget),
            retrieval=RetrievalService(tmp_path, {SourceType.WEB: search}),
            options=ResearchOptions(production_policy_version=2),
        ).run(ResearchRequest(question="A request requiring meaningful classification."), budget)
    )
    assert state["stop_reason"] == "input_rejected"
    assert not state["research_questions"] and not state["calls"] and search.calls == 0
    assert len(requests) == 1
    assert any(e["kind"] == "input_review_" + category for e in state["events"].values())


@pytest.mark.parametrize(
    "result",
    [
        {"category": "research", "questions": []},
        {
            "category": "manipulation",
            "questions": [{"question": "Extra request?", "acceptance_criteria": ["extra"]}],
        },
    ],
)
def test_malformed_combined_review_cannot_reach_search(tmp_path, result):
    budget = BudgetLimits(max_model_calls=5)
    search = FixtureRetrievalAdapter()
    state = asyncio.run(
        ResearchService(
            tmp_path,
            model=adapter(lambda request: reply(result), budget),
            retrieval=RetrievalService(tmp_path, {SourceType.WEB: search}),
            options=ResearchOptions(production_policy_version=2),
        ).run(ResearchRequest(question="A request requiring meaningful classification."), budget)
    )
    assert state["run_status"] == "failed"
    assert not state["research_questions"] and search.calls == 0


def test_combined_review_approval_resume_uses_exactly_five_calls(tmp_path):
    fixture = FixtureResearchModel()
    titles = []
    budget = BudgetLimits(
        max_model_calls=5,
        max_subquestions=1,
        max_queries_per_pass=1,
        max_research_passes=1,
        max_searches=1,
        max_rewrites=0,
    )
    search = FixtureRetrievalAdapter()

    async def respond(request):
        payload = json.loads(request.content)
        title = payload["generationConfig"]["responseJsonSchema"]["title"]
        titles.append(title)
        value = json.loads(payload["contents"][0]["parts"][0]["text"])
        if title == "ReviewedPlanDraft":
            assert payload["generationConfig"]["thinkingConfig"]["thinkingLevel"] == "minimal"
            assert payload["generationConfig"]["maxOutputTokens"] == 1024
            assert (
                payload["generationConfig"]["responseJsonSchema"]["properties"]["questions"][
                    "maxItems"
                ]
                == 1
            )
            assert request.extensions["timeout"]["read"] == 45
            result = await fixture.plan(ResearchRequest.model_validate(value), max_questions=1)
            result["category"] = "research"
        elif title == "QueryBatchDraft":
            result = await fixture.generate_queries(QueryGenerationRequest.model_validate(value))
        elif title == "CoverageAssessment":
            result = await fixture.evaluate_coverage(CoverageInput.model_validate(value))
        elif title == "QuoteSelectionDraft":
            result = {
                "claims": [
                    {"evidence_id": item["id"], "question_ids": item["question_ids"]}
                    for item in value["evidence"]
                ]
            }
        else:
            result = await fixture.critique(CriticInput.model_validate(value))
        return reply(result)

    def service():
        return ResearchService(
            tmp_path,
            model=adapter(respond, budget),
            retrieval=RetrievalService(tmp_path, {SourceType.WEB: search}),
            options=ResearchOptions(
                production_policy_version=2, require_plan_approval=True, node_timeout_seconds=60
            ),
        )

    paused = asyncio.run(
        service().run(
            ResearchRequest(question="Compare solar and wind electricity output."), budget
        )
    )
    assert paused["approval_status"] == "awaiting_approval"
    assert len(titles) == 1 and search.calls == 0
    assert any(e["kind"] == "input_review_research" for e in paused["events"].values())
    completed = asyncio.run(
        service().resume(
            paused["thread_id"],
            decision=PlanDecision(approved=True, plan_version=paused["plan_version"]),
        )
    )
    assert completed["run_status"] == "completed"
    assert len(titles) == 5 and search.calls == 1
    assert completed["planning_attempts"] + completed["quality_attempts"] == 5
    assert asyncio.run(service().resume(paused["thread_id"])) == completed
    assert len(titles) == 5
