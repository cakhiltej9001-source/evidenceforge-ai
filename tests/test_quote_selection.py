"""Immutable quote selection and legacy paid receipt compatibility without network."""

import asyncio
import json

import pytest

from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService


class SelectorFixture(FixtureResearchModel):
    def __init__(self, problem=None):
        super().__init__(
            plan_output={
                "questions": [
                    {"question": "What determines alpha?", "acceptance_criteria": ["alpha"]},
                    {"question": "What determines beta?", "acceptance_criteria": ["beta"]},
                ]
            }
        )
        self.problem = problem
        self.selected = 0

    async def select_quotes(self, request):
        self.selected += 1
        claims = [
            {"evidence_id": item.id, "question_ids": list(item.question_ids)}
            for item in request.evidence
        ]
        if self.problem == "unknown_evidence":
            claims[0]["evidence_id"] = "evidence_missing"
        elif self.problem == "unknown_question":
            claims[0]["question_ids"] = ["question_missing"]
        elif self.problem == "unlinked_question":
            item = request.evidence[0]
            claims[0]["question_ids"] = [
                next(q.id for q in request.questions if q.id not in item.question_ids)
            ]
        elif self.problem == "edited_statement":
            claims[0]["statement"] = "Altered wording must never enter a quotation."
        return {"claims": claims}

    async def synthesize(self, request):
        if not self.problem:
            raise AssertionError("Current selector must not request free-text synthesis")
        return await super().synthesize(request)


def service(root, model, options=None):
    batch = RetrievalBatch(
        results=(
            RetrievedSource(
                title="Synthetic alpha fixture",
                url="https://example.org/alpha",
                content="Synthetic fixture: alpha depends on sunlight,  under stated conditions.",
            ),
            RetrievedSource(
                title="Synthetic beta fixture",
                url="https://example.org/beta",
                content="Synthetic fixture: beta depends on wind speed,  under stated conditions.",
            ),
        )
    )
    return ResearchService(
        root,
        model=model,
        options=options,
        retrieval=RetrievalService(root, {SourceType.WEB: FixtureRetrievalAdapter(batch)}),
    )


def test_selections_project_entire_authentic_passages_without_model_wording(tmp_path):
    model = SelectorFixture()
    app = service(tmp_path, model)
    state = asyncio.run(app.run(ResearchRequest(question="Compare alpha and beta production.")))
    assert state["run_status"] == "completed"
    assert model.selected == 1 and model.synthesis_calls == 0
    assert len(state["report_claims"]) == 2
    for claim in state["report_claims"].values():
        assert claim["kind"] == "fact" and not claim["qualifiers"]
        assert claim["statement"].endswith(",  under stated conditions.")
        for eid in claim["evidence_ids"]:
            assert claim["statement"] == state["evidence_store"][eid]["passage"]
    assert all(audit["support"] == "supported" for audit in state["citation_audit"])
    assert asyncio.run(app.resume(state["thread_id"])) == state
    assert model.selected == 1


@pytest.mark.parametrize(
    "problem", ["unknown_evidence", "unknown_question", "unlinked_question", "edited_statement"]
)
def test_invalid_selection_or_model_text_fails_closed(tmp_path, problem):
    model = SelectorFixture(problem)
    state = asyncio.run(
        service(tmp_path, model).run(ResearchRequest(question="Compare alpha and beta production."))
    )
    assert state["stage_error"] == "synthesis"
    assert not state["report_claims"] and not state["final_report"]
    assert model.selected == 1 and model.synthesis_calls == 0
    assert "Altered wording" not in json.dumps(state)
