"""Adversarial layout and missing-data checks for new contract-version-6 runs."""

import pytest
from test_report_quality_guards import TABLE, reopen_with_guard, run

from evidenceforge.evidence.text_quality import (
    absence_supported,
    aligned_table,
    ambiguous_flat_table,
    quality_spans,
)
from evidenceforge.reporting import finalize, render_report

ALIGNED = (
    "| Earth atmosphere gas | Percentage |\n| --- | --- |\n| Nitrogen | 78% |\n| Oxygen | 21% |"
)


@pytest.mark.parametrize("separator", ["\n", "\t", " | "])
def test_delimiter_alone_cannot_make_flattened_rows_safe(separator):
    text = TABLE.replace(" Mars ", separator + "Mars ")
    assert ambiguous_flat_table(text)


@pytest.mark.parametrize(
    "text",
    [
        ALIGNED,
        "Earth atmosphere gas\tPercentage\nNitrogen\t78%\nOxygen\t21%",
    ],
)
def test_explicit_consistent_headers_and_rows_are_preserved(text):
    assert aligned_table(text)
    assert not ambiguous_flat_table(text)
    assert list(quality_spans(text, 1200)) == [(0, len(text))]


@pytest.mark.parametrize(
    "text",
    [
        "| Gas | Percentage |\n| Nitrogen | 78% | extra |",
        "| | Percentage |\n| Nitrogen | 78% |",
        "| Gas | Percentage |\n| --- | --- |",
    ],
)
def test_inconsistent_or_missing_headers_are_not_validated(text):
    assert not aligned_table(text)


def test_exercise_ends_at_paragraph_boundary_and_offsets_stay_exact():
    prose = "Earth atmosphere contains nitrogen."
    text = "Problem 5 - Compare hydrogen. Answer: Hydrogen is abundant.\n\n" + prose
    found = [text[a:b] for a, b in quality_spans(text, 1200)]
    assert found[-1] == prose
    assert found[0].startswith("Problem 5")


@pytest.mark.parametrize(
    "statement",
    [
        "Solar generation is not reported.",
        "Wind generation is not missing.",
        "Wind generation is not unavailable.",
        "No data are missing for wind generation.",
        "No wind generation percentages are missing.",
        "Wind generation is measured. Solar generation is missing.",
    ],
)
def test_unrelated_or_negated_absence_does_not_satisfy_wind_criterion(statement):
    assert not absence_supported("State missing wind generation percentages.", [statement])


def test_relevant_explicit_absence_is_supported():
    assert absence_supported(
        "State missing wind generation percentages.",
        ["Wind generation percentages are not reported."],
    )


def test_new_finalizer_requires_absence_in_the_criterion_subject_clause(tmp_path):
    state = reopen_with_guard(
        run(
            tmp_path,
            "Earth atmosphere is described. Wind generation is measured. "
            "Solar generation is not reported.",
            version=4,
        )
    )
    for event in state["events"].values():
        if event["kind"] == "report_quality_guard":
            event["kind"] = "report_quality_guard_v2"
    state["research_questions"][0]["acceptance_criteria"] = [
        "State missing wind generation percentages.",
    ]
    updated = {**state, **finalize(state)}
    assert updated["run_status"] == "partial"
    assert updated["coverage_status"] == "missing"
    assert any("missing-data inventory" in g["missing_aspect"] for g in updated["gaps"])


def test_new_run_preserves_and_renders_aligned_table_layout(tmp_path):
    state = run(tmp_path, ALIGNED, version=6)
    assert any(e["passage"] == ALIGNED for e in state["evidence_store"].values())
    report = render_report(state)
    assert ALIGNED in report
    assert "text\n" + ALIGNED in report
    assert any(e["kind"] == "report_quality_guard_v2" for e in state["events"].values())


def test_new_run_recovers_useful_prose_after_exercise_paragraph(tmp_path):
    prose = "Earth atmosphere contains nitrogen."
    state = run(
        tmp_path,
        "Problem 5 - Describe Earth atmosphere. Answer: Calculate a mass.\n\n" + prose,
        version=6,
    )
    passages = [e["passage"] for e in state["evidence_store"].values()]
    assert passages == [prose]
