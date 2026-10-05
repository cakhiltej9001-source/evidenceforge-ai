"""Safety gates for deduplicated model input and unchanged source provenance."""

import asyncio
import json

from evidenceforge.evidence.deduplication import working_evidence
from evidenceforge.exports import report_export
from evidenceforge.graph.state import StateSnapshot
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.reporting import render_report
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService


def test_containment_never_discards_distinct_questions_owners_or_qualifiers(populated_state):
    original = StateSnapshot.model_validate(populated_state).evidence_store["evidence_1"]
    copy = original.model_copy(update={"id": "copy", "source_id": "copy_source"})
    broader = original.model_copy(
        update={
            "id": "broader",
            "source_id": "broader_source",
            "passage": "Intro. " + original.passage + " Limitations.",
        }
    )
    different_question = original.model_copy(
        update={"id": "different_question", "question_ids": ("q_2",)}
    )
    different_owner = original.model_copy(update={"id": "different_owner", "owner_scope": "other"})
    qualified = original.model_copy(
        update={"id": "qualified", "passage": original.passage + " Only in winter."}
    )
    partial = original.model_copy(
        update={"id": "partial", "passage": "Synthetic evidence: different finding."}
    )

    def correct_span(changed):
        return changed.model_copy(
            update={
                "locator": changed.locator.model_copy(
                    update={
                        "end_offset": changed.locator.start_offset + len(changed.passage),
                    }
                )
            }
        )

    broader, qualified, partial = map(correct_span, (broader, qualified, partial))
    result = working_evidence(
        [copy, original, broader, different_question, different_owner, qualified, partial]
    )
    assert {e.id for e in result.evidence} == {
        "broader",
        "different_question",
        "different_owner",
        "qualified",
        "partial",
    }
    assert {d.evidence_id for d in result.duplicates} == {"copy", "evidence_1"}
    for duplicate in result.duplicates:
        assert (
            broader.passage[duplicate.representative_start : duplicate.representative_end]
            == original.passage
        )
        assert duplicate.locator == original.locator
        assert duplicate.acquisition_ids == original.acquisition_ids
    assert (
        working_evidence(
            reversed(
                [copy, original, broader, different_question, different_owner, qualified, partial]
            )
        )
        == result
    )


class ObservedModel(FixtureResearchModel):
    def __init__(self):
        super().__init__(
            plan_output={
                "questions": [
                    {
                        "question": "What determines solar electricity output?",
                        "acceptance_criteria": ["solar electricity output"],
                    }
                ]
            }
        )
        self.inputs = []

    async def evaluate_coverage(self, request):
        self.inputs.append(request)
        return await super().evaluate_coverage(request)

    async def synthesize(self, request):
        self.inputs.append(request)
        return await super().synthesize(request)

    async def critique(self, request):
        self.inputs.append(request)
        return await super().critique(request)


def test_cross_source_dedup_preserves_every_span_and_audits_exact_copy_citations(tmp_path):
    quote = "Synthetic fixture: solar electricity output depends on sunlight."
    sources = RetrievalBatch(
        results=tuple(
            RetrievedSource(
                title=title,
                url=url,
                content=content,
            )
            for title, url, content in (
                ("Original synthetic source", "https://example.org/original", quote),
                (
                    "Copied synthetic source",
                    "https://example.org/copy",
                    "Publisher introduction.\n\n" + quote,
                ),
                (
                    "Contained synthetic passage",
                    "https://example.org/contained",
                    "solar electricity output",
                ),
            )
        )
    )
    adapter = FixtureRetrievalAdapter(sources)
    retrieval = RetrievalService(tmp_path, {SourceType.WEB: adapter})
    model = ObservedModel()
    service = ResearchService(tmp_path, model=model, retrieval=retrieval)
    state = asyncio.run(service.run(ResearchRequest(question="Research solar electricity output.")))
    assert state["run_status"] == "completed"
    assert len(state["evidence_store"]) == len(state["source_records"]) == 3
    assert len(state["report_claims"]) == 1
    assert len(model.inputs) == 3
    assert all(
        len(request.evidence) == 1 and len(request.duplicate_evidence) == 2
        for request in model.inputs
    )
    claim = next(iter(state["report_claims"].values()))
    assert claim["statement"] == quote
    assert len(claim["evidence_ids"]) == 2  # The shorter span cannot support the full quote.
    for eid in claim["evidence_ids"]:
        assert state["evidence_store"][eid]["passage"] == quote
        assert any(link["evidence_id"] == eid for link in state["claim_evidence_map"].values())
    assert all(a["support"] == "supported" for a in state["citation_audit"])
    assert len(state["final_report"]["source_ids"]) == 2
    markdown = render_report(state)
    assert "Original source spans remain retained" in markdown
    assert "copies do not establish independent corroboration" in markdown
    exported = json.loads(report_export(state))["deduplication"]
    assert exported["retained_passages"] == 3 and exported["working_passages"] == 1
    assert len(exported["duplicates"]) == 2
    for duplicate in exported["duplicates"]:
        original = state["evidence_store"][duplicate["evidence_id"]]
        assert duplicate["locator"] == original["locator"]
        assert duplicate["source_id"] == original["source_id"]
    calls_before = adapter.calls
    resumed = asyncio.run(
        ResearchService(tmp_path, model=ObservedModel(), retrieval=retrieval).resume(
            state["thread_id"]
        )
    )
    assert resumed == state and adapter.calls == calls_before
