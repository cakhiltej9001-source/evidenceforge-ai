"""Regressions for ambiguous tables and falsely sufficient final reports."""

import asyncio

from evidenceforge.identity import stable_id
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.nodes.extraction import ambiguous_table, safe_spans
from evidenceforge.reporting import finalize, render_report
from evidenceforge.research import ResearchOptions
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService

TABLE = (
    "Object Mass Carbon Dioxide Nitrogen Oxygen Argon "
    "Earth 1.4x1021 78% 21% 1% <1% Mars 2.5x1016 95% 2.7% 1.6% 0.7% "
    "All planets have an atmosphere."
)
PROSE = "Earth atmosphere contains nitrogen at 78 percent and oxygen at 21 percent."
EXERCISE = "Problem 5 - Compare hydrogen. Answer: The sun has hydrogen."


def run(root, text, version=5):
    model = FixtureResearchModel(
        plan_output={
            "questions": [
                {
                    "question": "What is the Earth atmosphere composition?",
                    "acceptance_criteria": ["Earth atmosphere"],
                }
            ]
        }
    )
    batch = RetrievalBatch(
        results=(
            RetrievedSource(
                title="Synthetic atmospheric evidence",
                url="https://example.org/atmosphere",
                content=text,
            ),
        )
    )
    service = ResearchService(
        root,
        model=model,
        options=ResearchOptions(quote_selection_version=version),
        retrieval=RetrievalService(root, {SourceType.WEB: FixtureRetrievalAdapter(batch)}),
    )
    return asyncio.run(service.run(ResearchRequest(question="Describe Earth atmosphere.")))


def reopen_with_guard(state):
    state["run_status"] = "running"
    state["finished_at"] = None
    identifier = stable_id("test_guard", state["run_id"])
    state["events"][identifier] = {
        "id": identifier,
        "kind": "report_quality_guard",
        "message": "Synthetic test guard",
    }
    return state


def test_flattened_table_detected_without_rejecting_prose_or_delimited_rows():
    assert ambiguous_table(TABLE)
    assert not ambiguous_table(PROSE)
    assert not ambiguous_table(TABLE.replace(" Mars ", "\nMars "))
    assert not ambiguous_table("Entity | Nitrogen | Oxygen\nEarth | 78% | 21%")


def test_exercise_block_keeps_exact_offsets_and_separates_useful_prose():
    text = PROSE + " " + EXERCISE
    pieces = [text[a:b].strip() for a, b in safe_spans(text, 1200)]
    assert pieces == [PROSE, EXERCISE]


def test_new_extraction_omits_ambiguous_table_and_whole_exercise_block(tmp_path):
    state = run(tmp_path, TABLE + "\n\n" + PROSE + " " + EXERCISE)
    retained = [e["passage"] for e in state["evidence_store"].values()]
    assert retained == [PROSE]
    assert all("Problem" not in c["statement"] for c in state["report_claims"].values())
    assert any("column associations" in r["rationale"] for r in state["rejected_evidence"].values())
    assert any(e["kind"] == "report_quality_guard" for e in state["events"].values())


def test_legacy_extraction_keeps_its_contract(tmp_path):
    state = run(tmp_path, TABLE, version=4)
    assert any(ambiguous_table(e["passage"]) for e in state["evidence_store"].values())
    assert not any(e["kind"] == "report_quality_guard" for e in state["events"].values())


def test_missing_inventory_cannot_be_claimed_complete_by_numeric_quote(tmp_path):
    state = reopen_with_guard(run(tmp_path, PROSE, version=4))
    state["research_questions"][0]["acceptance_criteria"] = [
        "List the Earth atmosphere composition.",
        "Explicitly state any missing primary gas percentages.",
    ]
    updated = {**state, **finalize(state)}
    assert updated["run_status"] == "partial"
    assert updated["coverage_status"] == "missing"
    assert any("missing-data inventory" in g["missing_aspect"] for g in updated["gaps"])
    assert "Unmet task criterion" in render_report(updated)


def test_finalizer_omits_ambiguous_selected_table_even_if_citation_is_exact(tmp_path):
    state = reopen_with_guard(run(tmp_path, TABLE, version=4))
    updated = {**state, **finalize(state)}
    assert updated["run_status"] != "completed"
    assert not updated["report_claims"]
    assert any("ambiguous numeric table" in g["missing_aspect"] for g in updated["gaps"])


def test_explicit_missing_data_quote_is_not_forced_partial(tmp_path):
    state = reopen_with_guard(
        run(tmp_path, PROSE + " Earth atmosphere argon percentage is not reported.", version=4)
    )
    state["research_questions"][0]["acceptance_criteria"] = [
        "Explicitly state missing gas percentages."
    ]
    updated = {**state, **finalize(state)}
    assert updated["run_status"] == "completed"
    assert not any("missing-data inventory" in g["missing_aspect"] for g in updated["gaps"])
