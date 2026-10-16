"""Short answers precede findings without inventing facts or hiding qualifiers."""

import asyncio
import json

import pytest

from evidenceforge.answering import answer_excerpts, unresolved_answer
from evidenceforge.graph.state import StateSnapshot
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.reporting import escape, render_report
from evidenceforge.research import ResearchOptions
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import ReportSection, ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService


def report_for(root, passages, question="What is the capital of Telangana state?"):
    model = FixtureResearchModel(
        plan_output={
            "questions": [
                {
                    "question": question,
                    "acceptance_criteria": ["Telangana" if "Telangana" in question else "Mars"],
                }
            ]
        }
    )
    batch = RetrievalBatch(
        results=tuple(
            RetrievedSource(
                title=f"Synthetic test source {index}",
                url=f"https://example.org/source-{index}",
                content=passage,
            )
            for index, passage in enumerate(passages)
        )
    )
    service = ResearchService(
        root,
        model=model,
        options=ResearchOptions(quote_selection_version=3),
        retrieval=RetrievalService(root, {SourceType.WEB: FixtureRetrievalAdapter(batch)}),
    )
    state = asyncio.run(service.run(ResearchRequest(question=question)))
    assert state["final_report"] and state["report_claims"]
    return state


def answer_section(markdown):
    return markdown.split("## Answer\n\n", 1)[1].split("## Key Findings", 1)[0]


@pytest.mark.parametrize(
    "sentence",
    ["Hyderabad is the capital of Telangana.", "The capital of Telangana is Hyderabad."],
)
def test_answer_precedes_findings_and_selects_the_clean_exact_sentence(tmp_path, sentence):
    state = report_for(
        tmp_path,
        [
            "May be an image of a building. Follow Original audio. Telangana capital facts.",
            sentence + " Hyderabad has a large population.",
        ],
    )
    before = json.dumps(state, sort_keys=True)
    snapshot = StateSnapshot.model_validate(state)
    excerpts = answer_excerpts(snapshot)
    assert len(excerpts) == 1 and excerpts[0].text == sentence
    excerpt = excerpts[0]
    evidence = snapshot.evidence_store[excerpt.evidence_id]
    assert evidence.passage[excerpt.start_offset : excerpt.end_offset] == sentence
    markdown = render_report(state, answer_first=True, local_source_links=True)
    answer = answer_section(markdown)
    number = snapshot.final_report.source_ids.index(evidence.source_id) + 1
    assert escape(sentence) in answer
    assert f"[{number}](#saved-source-{number})" in answer
    assert "Follow Original audio" not in answer
    assert "Supported quotation Q" not in answer
    assert "## Summary" not in markdown
    assert markdown.index("## Answer") < markdown.index("## Key Findings")
    assert "## Summary" in render_report(state)  # Legacy/default delivery remains compatible.
    assert json.dumps(state, sort_keys=True) == before


@pytest.mark.parametrize(
    "qualifier", ["This figure excludes trace components.", "This statement is false."]
)
def test_scope_qualifier_and_decimal_stay_with_the_answer(tmp_path, qualifier):
    passage = "Mars atmosphere contains 95.9 percent carbon dioxide. " + qualifier
    state = report_for(
        tmp_path, [passage], "What percentage of the Mars atmosphere is carbon dioxide?"
    )
    excerpts = answer_excerpts(StateSnapshot.model_validate(state))
    assert len(excerpts) == 1 and excerpts[0].text == passage
    assert escape("95.9") in answer_section(render_report(state, answer_first=True))
    assert escape(qualifier) in answer_section(render_report(state, answer_first=True))


def mark_disagreement(state, claim_ids):
    snapshot = StateSnapshot.model_validate(state)
    report = snapshot.final_report
    report = report.model_copy(
        update={
            "sections": tuple(s for s in report.sections if s.name != "disagreements")
            + (ReportSection(name="disagreements", claim_ids=tuple(claim_ids)),)
        }
    )
    return snapshot.model_copy(update={"final_report": report, "draft_report": report})


def test_disputed_answer_is_not_replaced_with_one_source_winner(tmp_path):
    state = report_for(
        tmp_path,
        ["Hyderabad is the capital of Telangana.", "Warangal is the capital of Telangana."],
    )
    snapshot = mark_disagreement(state, state["report_claims"])
    assert unresolved_answer(snapshot) and answer_excerpts(snapshot) == ()
    markdown = render_report(snapshot.model_dump(mode="json"), answer_first=True)
    answer = answer_section(markdown)
    assert "single answer is not established" in answer
    assert "Hyderabad" not in answer and "Warangal" not in answer
    assert "Hyderabad" in markdown and "Warangal" in markdown


def test_unrelated_difference_does_not_hide_a_supported_capital_answer(tmp_path):
    state = report_for(
        tmp_path, ["Hyderabad is the capital of Telangana.", "Telangana population is 35 million."]
    )
    population = [
        cid for cid, claim in state["report_claims"].items() if "population" in claim["statement"]
    ]
    assert population
    snapshot = mark_disagreement(state, population)
    assert not unresolved_answer(snapshot)
    assert answer_excerpts(snapshot)[0].text == "Hyderabad is the capital of Telangana."


def test_uncited_evidence_does_not_become_an_answer(populated_state):
    snapshot = StateSnapshot.model_validate(populated_state)
    assert snapshot.evidence_store and answer_excerpts(snapshot) == ()
    answer = answer_section(render_report(populated_state, answer_first=True))
    assert "concise supported answer could not be extracted" in answer
    assert "Synthetic evidence" not in answer
