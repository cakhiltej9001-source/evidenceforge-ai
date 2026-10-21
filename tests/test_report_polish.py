"""Editorial regressions from the completed hosted report; no paid providers."""

import asyncio
import re
from copy import deepcopy
from io import BytesIO

import pytest
from pypdf import PdfReader

from evidenceforge.answering import answer_excerpts, criterion_fit, criterion_label
from evidenceforge.graph.state import StateSnapshot
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.presentation import clean_spans, display_issues, promotional
from evidenceforge.report_pdf import PdfExportError, _inline, report_pdf
from evidenceforge.reporting import escape, render_report
from evidenceforge.research import ResearchOptions
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService


@pytest.mark.parametrize("apostrophe", ["'", "\u2019"])
def test_named_course_benefits_are_promotional(apostrophe):
    text = f"ExampleCo{apostrophe}s Machine Learning courses cover algorithms, helping learners."
    assert promotional(text)
    assert not promotional("AI education can include university courses and independent study.")


def test_missing_question_and_publication_metadata_are_not_highlighted():
    for text in (
        "Yes, because Python provides machine learning libraries.",
        "Updated on August 13, 2026 content AI engineers build systems.",
    ):
        assert display_issues(text, year=2026, request="AI engineering")
    text = "Apply for AI internships or junior roles. Where do AI engineers work?"
    spans = list(clean_spans(text, year=2026, request="AI engineering"))
    assert [text[a:b] for a, b in spans] == ["Apply for AI internships or junior roles."]
    caveat = "Python is useful. You don't need every library."
    assert [caveat[a:b] for a, b in clean_spans(caveat, year=2026, request="Python")] == [caveat]
    negative = "No specific degree is required for AI engineering."
    assert not display_issues(negative, year=2026, request="AI engineering")


@pytest.fixture
def polished_report(tmp_path):
    criteria = ["Python", "linear algebra", "frameworks", "projects", "entry-level career roles"]
    passages = [
        "An AI engineer uses Python programming languages to build models.",
        "An AI engineer learns linear algebra, probability and statistics.",
        "An AI engineer uses frameworks including TensorFlow and PyTorch.",
        "An AI engineer builds small projects (a spam classifier or recommendation system).",
        "An AI engineer can apply for entry-level career roles, "
        "including internships and junior positions. "
        "Where do AI engineers work?",
        "ExampleCo's AI engineer courses cover mathematics, helping learners build models.",
        "Yes, because an AI engineer uses Python for data science.",
        "Updated on August 13, 2026 content An AI engineer builds systems.",
    ]
    batch = RetrievalBatch(
        results=tuple(
            RetrievedSource(
                title=f"Synthetic editorial case {i}",
                url=f"https://example.org/{i}",
                content="\n\n".join(passages[i : i + 4]),
            )
            for i in range(0, len(passages), 4)
        )
    )
    model = FixtureResearchModel(
        plan_output={
            "questions": [
                {
                    "question": "How to become an AI engineer?",
                    "acceptance_criteria": criteria,
                }
            ]
        }
    )
    return asyncio.run(
        ResearchService(
            tmp_path,
            model=model,
            options=ResearchOptions(quote_selection_version=3),
            retrieval=RetrievalService(tmp_path, {SourceType.WEB: FixtureRetrievalAdapter(batch)}),
        ).run(
            ResearchRequest(question="How to become an AI engineer?"),
            BudgetLimits(max_subquestions=1),
        )
    )


def test_distinct_steps_and_sequential_findings_preserve_original_records(polished_report):
    before = deepcopy(polished_report)
    snapshot = StateSnapshot.model_validate(polished_report)
    excerpts = answer_excerpts(snapshot)
    assert any("spam classifier" in e.text for e in excerpts)
    assert any("internships" in e.text for e in excerpts)
    for e in excerpts:
        assert (
            snapshot.evidence_store[e.evidence_id].passage[e.start_offset : e.end_offset] == e.text
        )
    text = render_report(polished_report, answer_first=True, include_evidence_details=False)
    highlighted = text.split("## Sources", 1)[0]
    assert "ExampleCo" not in highlighted and "Yes, because" not in highlighted
    assert "Updated on" not in highlighted and "**Q" not in highlighted
    numbers = [int(n) for n in re.findall(r"\*\*Finding (\d+)\.\*\*", text)]
    assert numbers and numbers == list(range(1, len(numbers) + 1))
    assert "Evidence `" not in text
    assert "## Summary" in render_report(polished_report)
    assert polished_report == before


def test_report_pdf_has_searchable_report_and_sources_without_app_debug_panels(polished_report):
    pytest.importorskip("reportlab")
    before = deepcopy(polished_report)
    data = report_pdf(polished_report)
    reader = PdfReader(BytesIO(data))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert data.startswith(b"%PDF") and len(reader.pages) >= 1
    assert all(
        label in text for label in ("Research question", "Answer", "Key Findings", "Sources")
    )
    assert "Finding 1" in text and "completed" in text
    assert "Evidence `" not in text and "source_records" not in text
    assert "ExampleCo's AI courses" not in text
    assert any(page.get("/Annots") for page in reader.pages)
    assert polished_report == before


def test_pdf_does_not_upgrade_partial_status_or_interpret_source_markup(polished_report):
    pytest.importorskip("reportlab")
    state = deepcopy(polished_report)
    state.update(run_status="partial", stop_reason="pass_limit")
    pdf = PdfReader(BytesIO(report_pdf(state)))
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "partial" in text and "pass_limit" in text
    assert "&lt;img" in _inline('<img src="https://example.org/a">')
    assert "<link" not in _inline("[click](javascript:alert(1))")


def test_pdf_refuses_unsupported_characters_instead_of_corrupting_text(polished_report):
    pytest.importorskip("reportlab")
    state = deepcopy(polished_report)
    state["request"]["question"] = "\u4e2d\u6587"
    with pytest.raises(PdfExportError, match="font"):
        report_pdf(state)


def test_numbered_sections_keep_each_items_qualifiers():
    text = (
        "Programming (Foundation Skill) Learn Python and libraries. "
        "2. Mathematics (Conceptual Understanding) You don't need every advanced topic, "
        "but study linear algebra and statistics. 3."
    )
    spans = list(clean_spans(text, year=2026, request="AI engineer"))
    math = [text[a:b] for a, b in spans if "Mathematics" in text[a:b]]
    assert math and "don't" in math[0] and "but study" in math[0]
    assert "Programming" not in math[0]
    assert not display_issues(text, year=2026, request="AI engineer", editorial=False)


def test_flattened_action_list_does_not_attach_the_next_item_number():
    text = (
        "Build small projects (a spam classifier). 4. Learn deep learning frameworks "
        "5. Deploy models using APIs 6. Apply for junior roles."
    )
    values = [text[a:b] for a, b in clean_spans(text, year=2026, request="AI engineer")]
    assert "Build small projects (a spam classifier)." in values
    assert "Learn deep learning frameworks" in values
    assert "Deploy models using APIs" in values


def test_career_criteria_select_progression_instead_of_salary_or_generic_tools():
    criterion = (
        "Outline professional progression steps, including entry-level role transitions "
        "and practical skill acquisition methods."
    )
    assert criterion_label(criterion) == "Career steps"
    assert criterion_fit(criterion, "Core Skills: Python, Docker, TensorFlow.", "AI career") is None
    assert criterion_fit(criterion, "Career progression is important.", "AI career") is None
    text = (
        "AI Engineer Career Path\nThe typical career progression looks like this:\n"
        "1. AI Intern: Entry point for graduates, focused on learning tools.\n"
        "2. Junior AI Engineer: Building and testing models under guidance.\n"
        "3. AI Engineer: Independently building and deploying models.\n4."
    )
    values = [text[a:b] for a, b in clean_spans(text, year=2026, request="AI career")]
    assert len(values) == 1 and values[0].endswith("deploying models.")
    assert "under guidance" in values[0]
    assert criterion_fit(criterion, values[0], "AI career") is not None


def test_generic_math_mention_cannot_stand_in_for_requested_foundation_list():
    criterion = "List essential mathematical and statistical foundations required for AI/ML roles."
    assert (
        criterion_fit(
            criterion,
            "Core skills include Python programming, mathematics and statistics, MLOps, "
            "and communication abilities.",
            "How to become an AI engineer?",
        )
        is None
    )
    assert (
        criterion_fit(
            criterion,
            "Mathematical foundations include linear algebra, probability and calculus.",
            "How to become an AI engineer?",
        )
        is not None
    )
    assert (
        criterion_fit(
            "Describe three distinct portfolio project types that demonstrate AI engineering.",
            "Begin with practical exercises like predictive models, image recognition, "
            "chatbots, or recommendation engines.",
            "How to become an AI engineer?",
        )
        is not None
    )


def test_unrequested_career_asides_and_source_bibliography_do_not_become_highlights():
    text = (
        "Entry-level roles offer $100,000 annually. "
        "Core Skills: Python, Docker and TensorFlow. "
        "Most learners take between 6 and 18 months depending on their starting point. "
        "Production architectures reduce latency [17,1]. "
        "Creating a RAG assistant is a portfolio project."
    )
    values = [
        text[a:b] for a, b in clean_spans(text, year=2026, request="How to become an AI engineer?")
    ]
    assert values == [
        "Core Skills: Python, Docker and TensorFlow.",
        "Creating a RAG assistant is a portfolio project.",
    ]
    assert not display_issues(
        "Entry-level roles offer $100,000 annually.", year=2026, request="AI engineer salaries"
    )
    assert not display_issues(
        "Most learners take between 6 and 18 months.",
        year=2026,
        request="How long does it take to become an AI engineer?",
    )
    assert not display_issues(text, year=2026, request="AI career", editorial=False)


def test_concise_answer_discloses_missing_detailed_criteria_without_changing_saved_status(
    polished_report,
):
    state = deepcopy(polished_report)
    criterion = "List essential mathematical and statistical foundations required for AI roles."
    # This synthetic presentation check keeps historical status and audit records untouched.
    state["research_questions"][0]["acceptance_criteria"].append(criterion)
    # The cited fixture does name mathematical subjects, so use an unrelated inventory gap.
    missing = "List two distinct professional certifications accepted in AI engineering."
    state["research_questions"][0]["acceptance_criteria"].append(missing)
    before = deepcopy(state)
    text = render_report(state, answer_first=True, include_evidence_details=False)
    assert "Not established in the concise answer" in text and escape(missing) in text
    assert "recorded workflow status" in text
    assert state == before


def test_degree_acquisition_is_not_a_compensation_aside():
    assert not display_issues(
        "Earn a degree in computer science.",
        year=2026,
        request="How to become an AI engineer?",
    )
