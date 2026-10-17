"""Short answers precede findings without inventing facts or hiding qualifiers."""

import asyncio
import json

import pytest

from evidenceforge.answering import answer_excerpts, unresolved_answer
from evidenceforge.graph.state import StateSnapshot
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.presentation import clean_spans, display_issues, future_years
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


@pytest.mark.parametrize(
    "clutter",
    [
        "Join our course for placement support.",
        "Python skills [2:16] are important for an AI engineer.",
        "Photo by Example / Unsplash. Read more.",
        "| Phase | Months | Focus | Output |",
    ],
)
def test_clean_display_spans_skip_clutter_without_rewriting_it(clutter):
    useful = "Build Python projects and test the deployed model with realistic inputs."
    text = useful + "\n\n" + clutter
    spans = list(clean_spans(text, year=2026, request="How do I become an AI engineer?"))
    assert spans and text[slice(*spans[0])] == useful
    assert all(not display_issues(text[a:b], year=2026, request="AI engineer") for a, b in spans)
    assert clutter in text


def test_cleanup_abstains_when_it_would_detach_a_caveat():
    text = "Python is useful. However, join our course only if it meets your needs."
    assert not list(clean_spans(text, year=2026, request="How do I learn Python?"))


def test_future_date_detection_respects_an_explicit_requested_year():
    assert future_years("AI engineer requirements in 2027.", 2026, "AI engineer") == {2027}
    assert not future_years("Requirements in 2027.", 2026, "What is forecast for 2027?")
    assert not future_years("A history of AI in 2020.", 2026, "AI engineer")


def test_role_and_future_context_cannot_be_removed_to_make_an_excerpt_look_relevant():
    for text in (
        "A machine learning engineer builds production models. Learn Python and test projects.",
        "An AI engineer builds models. These are projected requirements for 2099.",
    ):
        assert not list(clean_spans(text, year=2026, request="How to become an AI engineer?"))


def test_noisy_findings_are_not_highlighted_but_evidence_and_status_are_preserved(tmp_path):
    clean = "An AI engineer builds Python projects and tests models before deployment."
    state = report_for(
        tmp_path,
        [
            clean,
            "An AI engineer should join our course for placement support.",
            "AI engineer requirements in 2099 include advanced software skills.",
            "AI engineer roadmap | Phase | Months | Skills | Output | "
            "Foundations | 2 | Python | App |",
        ],
        "How to become an AI engineer?",
    )
    original = json.dumps(state, sort_keys=True)
    markdown = render_report(state, answer_first=True, local_source_links=True)
    findings = markdown.split("## Key Findings", 1)[1].split("## Sources", 1)[0]
    assert escape(clean) in answer_section(markdown)
    assert "join our course" not in findings
    assert "roadmap \\|" not in findings
    assert "requirements in 2099" not in findings
    assert "**Date caution:**" in markdown
    assert "rather than highlighted" in markdown
    assert json.dumps(state, sort_keys=True) == original
    assert "join our course" in render_report(state)  # Historical default is still inspectable.


def test_concrete_how_to_excerpt_is_ranked_ahead_of_generic_introduction(tmp_path):
    useful = (
        "An AI engineer learns Python, builds tested projects and deploys models with monitoring."
    )
    state = report_for(
        tmp_path,
        ["An AI engineer needs a good educational foundation.", useful],
        "How to become an AI engineer?",
    )
    excerpts = answer_excerpts(StateSnapshot.model_validate(state))
    assert excerpts[0].text == useful
    assert "1. " in answer_section(render_report(state, answer_first=True))


def test_aligned_table_is_preserved_as_evidence_not_treated_as_broken_layout():
    table = "| Skill | Practice |\n| --- | --- |\n| Python | Build projects |"
    assert not display_issues(table, year=2026, request="AI engineering skills")
