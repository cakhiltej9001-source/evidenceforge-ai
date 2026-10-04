"""Offline Phase 6 behavior: comparable disputes, ranking, graphs, caps and resume."""

import asyncio
import hashlib
import json
from datetime import date

import pytest
from pydantic import ValidationError

from evidenceforge.evidence.contracts import AnalysisOptions, SourceQuality
from evidenceforge.evidence.projection import audit, project, render_inspection
from evidenceforge.evidence.propositions import compare, compare_all, extract
from evidenceforge.evidence.ranking import families, rank
from evidenceforge.graph.state import StateSnapshot, apply_update
from evidenceforge.nodes.intelligence import EvidenceIntelligence
from evidenceforge.research import ResearchOptions
from evidenceforge.retrieval.contracts import RetrievedSource
from evidenceforge.retrieval.fixtures import DisputeFixture, FixtureRetrievalAdapter
from evidenceforge.schemas import (
    BudgetLimits,
    EvidenceItem,
    EvidenceLocator,
    ResearchRequest,
    SourceRecord,
    SourceType,
)
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService

QUESTION = "What was Northfield solar electricity output?"


def passage(
    value="100",
    unit="GWh",
    year="2024",
    entity="Northfield solar",
    population="all plants",
    conditions="standard operation",
    metric="electricity output",
):
    return f"{entity} {metric} was {value} {unit} in {year} for {population} under {conditions}."


def evidence(text, suffix="1", question="q_1"):
    return EvidenceItem(
        id="evidence_" + suffix,
        source_id="source_" + suffix,
        owner_scope="local",
        acquisition_ids=("acquisition_" + suffix,),
        question_ids=(question,),
        passage=text,
        locator=EvidenceLocator(
            snapshot_id="snapshot_" + suffix, start_offset=0, end_offset=len(text)
        ),
        relevance=0.9,
        relevance_rationale="Synthetic direct lexical match.",
    )


@pytest.mark.parametrize(
    "other, expected",
    [
        (passage("120"), "contradicts"),
        (passage("100000", "MWh"), "supports"),
        (passage("0.1", "TWh"), "supports"),
        (passage("900", year="2023"), "not_comparable"),
        (passage("100", "MW"), "not_comparable"),
        (passage("900", entity="Northfield wind"), "not_comparable"),
        (passage("900", population="offshore plants"), "not_comparable"),
        (passage("900", conditions="storm operation"), "not_comparable"),
        (passage("900", metric="energy output"), "not_comparable"),
        (passage(), "duplicate"),
    ],
)
def test_comparison_scopes_units_and_duplicates(other, expected):
    a, b = extract(evidence(passage()))[0], extract(evidence(other, "2"))[0]
    c = compare(a, b)
    assert c.relationship == expected
    assert compare(b, a) == c
    if expected == "supports":
        assert c.normalized_left == c.normalized_right or float(c.normalized_left) == float(
            c.normalized_right
        )
        assert c.canonical_unit == "Wh"


@pytest.mark.parametrize(
    "text",
    [
        "Solar produces more energy.",
        "Solar output was 100 GWh.",
        passage(year="2024-02-31"),
        "No evidence supports this.",
    ],
)
def test_unknown_prose_and_invalid_dates_do_not_manufacture_dissent(text):
    assert extract(evidence(text)) == ()


def test_exact_offsets_decimal_and_pair_cap():
    text = "  " + passage("100.125") + "\n\n" + passage("100125", "MWh")
    item = evidence(text)
    props = extract(item)
    assert len(props) == 2
    assert all(item.passage[p.start_offset : p.end_offset] == p.quote for p in props)
    assert compare(*props).relationship == "supports"
    assert compare_all(props, 1)[1] is False
    more = props + extract(evidence(passage("120"), "2"))
    assert len(compare_all(more, 1)[0]) == 1
    assert compare_all(more, 1)[1] is True


def test_no_cross_question_comparison():
    a = extract(evidence(passage()))[0]
    b = extract(evidence(passage("120"), "2", "q_2"))[0]
    assert compare_all((a, b), 10) == ((), False)
    with pytest.raises(ValueError):
        compare(a, b)


def source(sid, text, **kwargs):
    return SourceRecord(
        id=sid,
        title=sid,
        source_type="web",
        provider="fixture",
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
        url="https://example.org/" + sid,
        **kwargs,
    )


def test_primary_outweighs_secondary_recency_unknowns_and_historical_policy():
    sources = {
        "source_1": source(
            "source_1",
            passage(),
            primary_evidence=True,
            methodology_transparent=True,
            publication_date="2020-01-01",
            publisher="Authored primary",
            metadata_rationale="Synthetic primary dataset metadata.",
        ),
        "source_2": source(
            "source_2",
            passage("120"),
            primary_evidence=False,
            methodology_transparent=False,
            publication_date="2026-09-30",
            publisher="Authored article",
            metadata_rationale="Synthetic secondary article metadata.",
        ),
    }
    items = {e.id: e for e in (evidence(passage()), evidence(passage("120"), "2"))}
    q = rank(sources, items, {}, (), "current", date(2026, 10, 1))
    assert q["source_1"].score > q["source_2"].score
    assert all(
        f.value is None for f in q["source_1"].features if f.name == "independent_corroboration"
    )
    h = rank(sources, items, {}, (), "historical", date(2026, 10, 1))
    assert next(f.weight for f in h["source_1"].features if f.name == "recency") == 0.0
    unknown = rank(
        {"source_1": source("source_1", passage())}, items, {}, (), "general", date(2026, 10, 1)
    )["source_1"]
    assert {f.name for f in unknown.features if f.value is None} >= {
        "primary_evidence",
        "methodology",
        "recency",
        "publisher_identity",
    }
    broken = unknown.model_dump(mode="json")
    broken["score"] = 0.99
    with pytest.raises(ValidationError):
        SourceQuality.model_validate(broken)


@pytest.mark.parametrize("date_text", ["nonsense", "2027-01-01"])
def test_unknown_invalid_future_publication_dates(date_text):
    q = rank(
        {"source_1": source("source_1", passage(), publication_date=date_text)},
        {},
        {},
        (),
        "current",
        date(2026, 10, 1),
    )["source_1"]
    assert next(f.value for f in q.features if f.name == "recency") is None


def test_copy_families_are_not_independent_votes():
    sources = {
        "source_1": source("source_1", passage(), source_family="family_a"),
        "source_2": source("source_2", passage(), source_family="family_b"),
        "source_3": source("source_3", passage("120"), source_family="family_b"),
    }
    groups = families(sources)
    assert len(set(groups.values())) == 1  # transitive shared content / family grouping
    assert groups == families(dict(reversed(list(sources.items()))))
    items = {
        e.id: e
        for e in (evidence(passage()), evidence(passage(), "2"), evidence(passage("120"), "3"))
    }
    props = {p.id: p for e in items.values() for p in extract(e)}
    comparisons = compare_all(tuple(props.values()), 10)[0]
    quality = rank(sources, items, props, comparisons, "general", date(2026, 10, 1))
    assert all(q.family_size == 3 for q in quality.values())
    assert all(
        f.value == 0.0
        for q in quality.values()
        for f in q.features
        if f.name == "independent_corroboration"
    )


def service(tmp_path, *, options=None, adapter=None):
    return ResearchService(
        tmp_path,
        retrieval=RetrievalService(tmp_path, {SourceType.WEB: adapter or DisputeFixture()}),
        options=options,
    )


def test_dispute_followup_preserves_passages_and_exports(tmp_path):
    adapter = DisputeFixture()
    svc = service(tmp_path, adapter=adapter)
    state = asyncio.run(
        svc.run(ResearchRequest(question=QUESTION), BudgetLimits(max_research_passes=2))
    )
    s = StateSnapshot.model_validate(state)
    assert s.run_status == "partial" and s.stop_reason == "pass_limit"
    assert s.iteration_count == 2 and s.coverage_status == "missing"
    assert any(q.status == "disputed" for q in s.coverage_by_question.values())
    assert {q.purpose for q in s.query_records.values()} >= {"counter_evidence", "primary_source"}
    assert {c.relationship for c in s.comparisons.values()} >= {
        "supports",
        "contradicts",
        "not_comparable",
        "duplicate",
    }
    assert len(s.evidence_store) == 5
    assert any(link.relationship == "contradicts" for link in s.claim_evidence_map.values())
    graph = project(state)
    known = {n.id for n in graph.nodes}
    assert all(e.source in known and e.target in known for e in graph.edges)
    assert any(e.relationship == "duplicate_of" for e in graph.edges)
    assert any(e.relationship == "contradicts" for e in graph.edges)
    for name, expected in [
        ("graph.json", graph.model_dump(mode="json")),
        ("audit.json", audit(state)),
    ]:
        assert (
            json.loads(svc.report_path(state).with_name(name).read_text(encoding="utf-8"))
            == expected
        )
    tampered = json.loads(json.dumps(state))
    conflict = next(
        c for c in tampered["comparisons"].values() if c["relationship"] == "contradicts"
    )
    conflict["relationship"] = "supports"
    with pytest.raises(ValidationError):
        StateSnapshot.model_validate(tampered)
    assert "contradicts" in svc.report_path(state).read_text(encoding="utf-8")
    assert "neutral value of 0.5" in render_inspection(state)
    cid = next(iter(s.report_claims))
    selected = project(state, cid)
    assert [n.id for n in selected.nodes if n.kind == "claim"] == [cid]
    assert any(n.kind == "evidence" for n in selected.nodes)
    with pytest.raises(ValueError):
        project(state, "claim_invented")
    broken = json.loads(json.dumps(state))
    next(iter(broken["claim_evidence_map"].values()))["evidence_id"] = "evidence_invented"
    with pytest.raises(ValidationError):
        project(broken)


def test_dispute_respects_search_limit(tmp_path):
    svc = service(tmp_path)
    state = asyncio.run(svc.run(ResearchRequest(question=QUESTION), BudgetLimits(max_searches=1)))
    assert state["run_status"] == "partial" and state["stop_reason"] == "search_limit"
    assert state["iteration_count"] == 1
    assert not any(q["purpose"] == "counter_evidence" for q in state["query_records"].values())
    assert any(c["relationship"] == "contradicts" for c in state["comparisons"].values())


def test_consistent_converted_values_skip_extra_search(tmp_path):
    adapter = FixtureRetrievalAdapter(
        {
            "results": [
                RetrievedSource(
                    title="A", url="https://a.example.org/", content=passage()
                ).model_dump(mode="json"),
                RetrievedSource(
                    title="B", url="https://b.example.org/", content=passage("100000", "MWh")
                ).model_dump(mode="json"),
            ]
        }
    )
    state = asyncio.run(service(tmp_path, adapter=adapter).run(ResearchRequest(question=QUESTION)))
    assert state["run_status"] == "completed" and state["iteration_count"] == 1
    assert not any(c["relationship"] == "contradicts" for c in state["comparisons"].values())
    assert not any(q["purpose"] == "counter_evidence" for q in state["query_records"].values())


def test_analysis_caps_disclose_partial_not_sufficient(tmp_path):
    options = ResearchOptions(analysis=AnalysisOptions(max_propositions=1, max_comparisons=1))
    state = asyncio.run(
        service(tmp_path, options=options).run(
            ResearchRequest(question=QUESTION), BudgetLimits(max_research_passes=1)
        )
    )
    assert state["run_status"] == "partial" and state["analysis_limited"] is True
    assert state["coverage_status"] == "missing" and state["gaps"]


def test_resume_after_extraction_rebuilds_analysis_and_terminal_redelivery(tmp_path):
    async def exercise():
        svc = service(tmp_path)
        paused = await svc.run(
            ResearchRequest(question=QUESTION),
            BudgetLimits(max_research_passes=2),
            pause_after="evidence_extractor",
        )
        assert paused["run_status"] == "running" and not paused["comparisons"]
        resumed = await service(tmp_path).resume(paused["thread_id"])
        assert resumed["run_status"] == "partial" and resumed["comparisons"]
        assert await service(tmp_path).resume(paused["thread_id"]) == resumed
        return resumed

    state = asyncio.run(exercise())
    assert state["last_analysis_pass"] == 2
    assert (
        sum(r["searches"] for r in state["reservations"].values() if r["status"] != "released") == 3
    )


def test_unknown_prose_analysis_no_votes_and_exact_projection_span(populated_state):
    state = apply_update(populated_state, {"iteration_count": 1, "run_status": "running"})
    updated = apply_update(state, EvidenceIntelligence(AnalysisOptions())(state))
    assert not updated["propositions"] and not updated["comparisons"]
    assert "unclassified" in updated["analysis_notes"][0]
    assert (
        EvidenceIntelligence(AnalysisOptions())(updated)["analysis_signature"]
        == updated["analysis_signature"]
    )


def test_tampered_numeric_fields_rejected(populated_state):
    # Build valid supporting records using the existing fixture IDs.
    original = StateSnapshot.model_validate(populated_state)
    old = original.evidence_store["evidence_1"]
    item = EvidenceItem.model_validate(
        {
            **old.model_dump(mode="json"),
            "passage": passage(),
            "locator": {**old.locator.model_dump(mode="json"), "end_offset": len(passage())},
        }
    )
    state = apply_update(populated_state, {"evidence_store": {}})
    data = json.loads(json.dumps(state))
    data["evidence_store"]["evidence_1"] = item.model_dump(mode="json")
    data["iteration_count"] = 1
    data["run_status"] = "running"
    analyzed = apply_update(data, EvidenceIntelligence(AnalysisOptions())(data))
    wrong = json.loads(json.dumps(analyzed))
    next(iter(wrong["propositions"].values()))["value"] = "999"
    with pytest.raises(ValidationError):
        StateSnapshot.model_validate(wrong)
    wrong = json.loads(json.dumps(analyzed))
    next(iter(wrong["propositions"].values()))["quote"] = "Invented quotation"
    with pytest.raises(ValidationError):
        StateSnapshot.model_validate(wrong)


def test_copy_group_identity_stays_stable():
    a = source("source_z", passage(), source_family="family_a")
    b = source("source_a", passage(), source_family="family_b")
    assert (
        families({"source_z": a})["source_z"]
        == families({"source_z": a, "source_a": b})["source_z"]
    )


@pytest.mark.parametrize(
    "text",
    [
        passage(unit="mW"),
        passage(unit="mWh"),
        passage(unit="gwh"),
        passage(conditions="30.5 degrees"),
    ],
)
def test_ambiguous_unit_case_and_decimal_condition_stay_unclassified(text):
    assert extract(evidence(text)) == ()
