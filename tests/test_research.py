"""Offline Phase 4 behavioral gates: routing, repair and report safety."""

import asyncio
import json
from pathlib import Path

import pytest

from evidenceforge.graph.state import StateSnapshot
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.reporting import render_report
from evidenceforge.research import CriticInput, ResearchOptions, SynthesisInput
from evidenceforge.research_demo import SecondPassFixture
from evidenceforge.retrieval.contracts import RetrievalBatch
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService

QUESTION = "Compare solar and wind electricity output."


def run(tmp_path: Path, *, model=None, adapter=None, budget=None, options=None):
    retrieval = RetrievalService(tmp_path, {SourceType.WEB: adapter}) if adapter else None
    service = ResearchService(tmp_path, model=model, retrieval=retrieval, options=options)
    state = asyncio.run(service.run(ResearchRequest(question=QUESTION), budget))
    StateSnapshot.model_validate(state)
    assert service.report_path(state).read_text(encoding="utf-8") == render_report(state)
    assert (
        json.loads(service.report_path(state).with_name("state.json").read_text(encoding="utf-8"))
        == state
    )
    return state


def test_immediate_sufficiency(tmp_path):
    model = FixtureResearchModel()
    state = run(tmp_path, model=model)
    assert (state["run_status"], state["iteration_count"], state["revision_count"]) == (
        "completed",
        1,
        0,
    )
    assert (model.coverage_calls, model.synthesis_calls, model.critic_calls) == (1, 1, 1)
    assert all(a["support"] == "supported" for a in state["citation_audit"])
    assert "## Summary" in render_report(state)
    assert "## Key Findings" in render_report(state)
    assert "## Sources" in render_report(state)


def test_second_pass_adds_new_evidence(tmp_path):
    adapter = SecondPassFixture()
    state = run(tmp_path, adapter=adapter)
    assert (state["run_status"], state["iteration_count"]) == ("completed", 2)
    assert {
        state["query_records"][a["query_id"]]["research_pass"]
        for a in state["source_acquisitions"].values()
    } == {1, 2}
    assert any("wind" in e["passage"] for e in state["evidence_store"].values())
    assert len(state["source_records"]) == 2
    assert not state["gaps"]


def test_no_evidence_stops_without_synthesis(tmp_path):
    model = FixtureResearchModel()
    state = run(tmp_path, model=model, adapter=FixtureRetrievalAdapter(RetrievalBatch(results=())))
    assert state["run_status"] == "insufficient_evidence"
    assert state["stop_reason"] == "no_evidence"
    assert state["iteration_count"] <= 3
    assert model.synthesis_calls == model.critic_calls == 0
    assert not state["report_claims"]
    assert "No supported claims" in render_report(state)


class BadThenGood(FixtureResearchModel):
    async def synthesize(self, request: SynthesisInput) -> object:
        response = await super().synthesize(request)
        assert isinstance(response, dict)
        if self.synthesis_calls == 1:
            response["claims"][0]["statement"] = "Solar produces 999 gigawatts everywhere."
        return response


def test_unsupported_claim_is_repaired_and_critic_repeated(tmp_path):
    model = BadThenGood()
    state = run(tmp_path, model=model)
    assert state["run_status"] == "completed"
    assert state["revision_count"] == 1
    assert model.synthesis_calls == model.critic_calls == 2
    assert all("999" not in c["statement"] for c in state["report_claims"].values())
    assert "Solar produces 999 gigawatts everywhere" not in render_report(state)
    assert state["draft_report"]["draft_version"] == 2


class MixedUnsupported(FixtureResearchModel):
    async def synthesize(self, request: SynthesisInput) -> object:
        response = await super().synthesize(request)
        assert isinstance(response, dict)
        response["claims"][0]["statement"] = "Unsupported secret number 999."
        return response


def test_exhausted_repairs_omit_unsupported_claim(tmp_path):
    state = run(tmp_path, model=MixedUnsupported(), budget=BudgetLimits(max_rewrites=1))
    assert state["run_status"] == "partial"
    assert state["stop_reason"] == "rewrite_limit"
    assert state["revision_count"] == 1
    assert len(state["unresolved_audits"]) == 1
    assert all("999" not in c["statement"] for c in state["report_claims"].values())
    assert "Unsupported secret number 999" not in render_report(state)
    assert "Omitted 1 claims" in render_report(state)


class CriticThenCitation(BadThenGood):
    async def critique(self, request: CriticInput) -> object:
        self.critic_calls += 1
        return (
            {"decision": "revise", "revision_brief": ["Keep source qualifiers."]}
            if self.critic_calls == 1
            else {"decision": "approved"}
        )

    async def synthesize(self, request: SynthesisInput) -> object:
        response = await FixtureResearchModel.synthesize(self, request)
        if self.synthesis_calls == 2:
            response["claims"][0]["statement"] = "Bad second draft."
        return response


def test_critic_and_citation_repairs_share_allowance(tmp_path):
    model = CriticThenCitation()
    state = run(tmp_path, model=model, budget=BudgetLimits(max_rewrites=1))
    assert state["revision_count"] == 1
    assert model.synthesis_calls == model.critic_calls == 2
    assert state["run_status"] == "partial"
    assert state["unresolved_audits"]


@pytest.mark.parametrize(
    "output",
    [
        {
            "claims": [
                {
                    "statement": "Unknown citation",
                    "question_ids": ["question_missing"],
                    "evidence_ids": ["evidence_missing"],
                }
            ]
        },
        {"claims": []},
        {"raw": "malformed"},
    ],
)
def test_malformed_draft_fails_sanitized(tmp_path, output):
    state = run(tmp_path, model=FixtureResearchModel(synthesis_output=output))
    assert state["run_status"] == "failed"
    assert state["stage_error"] == "synthesis"
    assert "Unknown citation" not in render_report(state)
    assert state["tool_errors"]


def test_pass_limit_returns_partial_with_gaps(tmp_path):
    state = run(tmp_path, adapter=SecondPassFixture(), budget=BudgetLimits(max_research_passes=1))
    assert (state["run_status"], state["stop_reason"]) == ("partial", "pass_limit")
    assert state["gaps"]
    assert "Unmet task criterion" in render_report(state)


def test_critic_exhaustion_is_partial(tmp_path):
    state = run(
        tmp_path,
        model=FixtureResearchModel(
            critic_output={"decision": "revise", "revision_brief": ["Review more evidence."]}
        ),
        budget=BudgetLimits(max_rewrites=0),
    )
    assert state["run_status"] == "partial"
    assert "critic still requested" in render_report(state)


def test_recursion_backstop(tmp_path):
    state = run(tmp_path, options=ResearchOptions(recursion_limit=6))
    assert state["stop_reason"] == "recursion_limit"
    assert state["run_status"] in {"failed", "partial"}


def test_quality_allowance_is_bounded(tmp_path):
    state = run(
        tmp_path,
        budget=BudgetLimits(max_model_calls=3, reserved_quality_calls=2),
        adapter=SecondPassFixture(),
    )
    assert state["quality_attempts"] + state["planning_attempts"] <= 3
    assert state["planning_attempts"] == 1
    assert state["iteration_count"] == 0
    assert state["run_status"] == "failed"


class Uncited(FixtureResearchModel):
    async def synthesize(self, request: SynthesisInput) -> object:
        response = await super().synthesize(request)
        response["claims"][0]["evidence_ids"] = []
        response["claims"][0]["kind"] = "recommendation"
        return response


def test_nonfact_label_cannot_bypass_citations(tmp_path):
    state = run(tmp_path, model=Uncited(), budget=BudgetLimits(max_rewrites=0))
    assert state["run_status"] == "partial"
    assert any(not a["structural_valid"] for a in state["unresolved_audits"])
    assert all(c["evidence_ids"] for c in state["report_claims"].values())


class MissingQualifier(FixtureResearchModel):
    async def synthesize(self, request: SynthesisInput) -> object:
        response = await super().synthesize(request)
        response["claims"][0]["qualifiers"] = ["during 2024 only"]
        return response


def test_absent_date_qualifier_fails_support(tmp_path):
    state = run(tmp_path, model=MissingQualifier(), budget=BudgetLimits(max_rewrites=0))
    assert state["unresolved_audits"]
    assert state["run_status"] == "partial"
    assert all("during 2024 only" not in c["qualifiers"] for c in state["report_claims"].values())
    assert "during 2024 only" not in render_report(state)


class CorruptSnapshot(FixtureResearchModel):
    def __init__(self, directory):
        super().__init__()
        self.directory = directory

    async def critique(self, request: CriticInput) -> object:
        for path in (self.directory / "artifacts").rglob("*.txt"):
            path.write_text("Changed snapshot", encoding="utf-8")
        return await super().critique(request)


def test_snapshot_integrity_failure_omits_claims(tmp_path):
    state = run(tmp_path, model=CorruptSnapshot(tmp_path), budget=BudgetLimits(max_rewrites=0))
    assert state["run_status"] == "insufficient_evidence"
    assert not state["report_claims"]
    assert state["unresolved_audits"]


def test_storage_failure_does_not_confirm_delivery(tmp_path, monkeypatch):
    def fail_write(*args):
        raise OSError("synthetic storage failure")

    monkeypatch.setattr("evidenceforge.services.research.atomic_write", fail_write)
    with pytest.raises(OSError):
        asyncio.run(ResearchService(tmp_path).run(ResearchRequest(question=QUESTION)))


def test_coverage_unknown_question_is_typed_failure(tmp_path):
    state = run(
        tmp_path,
        model=FixtureResearchModel(
            coverage_output={"questions": [{"question_id": "question_missing", "criteria": []}]}
        ),
    )
    assert state["run_status"] == "partial"
    assert state["stage_error"] == "coverage"
    assert state["stop_reason"] == "fatal_error"
    assert all(a["support"] == "supported" for a in state["citation_audit"])


def test_report_summary_paragraphs_and_per_source_evidence(tmp_path):
    state = run(tmp_path)
    markdown = render_report(state)
    summary = markdown.split("## Summary\n\n", 1)[1].split("## Key Findings", 1)[0].strip()
    paragraphs = summary.split("\n\n")
    assert 2 <= len(paragraphs) <= 3
    assert all(not paragraph.startswith("- ") and "[1]" in paragraph for paragraph in paragraphs)
    sources = markdown.split("## Sources\n\n", 1)[1].split("## Limitations", 1)[0]
    for claim in state["report_claims"].values():
        for eid in claim["evidence_ids"]:
            evidence = state["evidence_store"][eid]
            assert f"Evidence `{eid}`" in sources
            locator = evidence["locator"]
            assert f"offsets {locator['start_offset']}-{locator['end_offset']}" in sources
    assert all(a["support"] == "supported" for a in state["citation_audit"])


class SummaryOnly(FixtureResearchModel):
    async def synthesize(self, request: SynthesisInput) -> object:
        response = await super().synthesize(request)
        assert isinstance(response, dict)
        for claim in response["claims"]:
            claim["section"] = "summary"
        return response


@pytest.mark.parametrize("input_version", [1, 2])
def test_supported_summary_only_draft_has_findings_without_changing_frozen_v1(
    tmp_path, input_version
):
    state = run(
        tmp_path,
        model=SummaryOnly(),
        options=ResearchOptions(quality_input_version=input_version),
    )
    assert state["run_status"] == "completed"
    findings = next(
        section["claim_ids"]
        for section in state["final_report"]["sections"]
        if section["name"] == "key_findings"
    )
    if input_version == 1:
        assert findings == []
    else:
        assert set(findings) == set(state["report_claims"])
        assert all(audit["support"] == "supported" for audit in state["citation_audit"])
        markdown = render_report(state)
        section = markdown.split("## Key Findings\n\n", 1)[1].split("## Sources", 1)[0]
        assert "solar electricity output" in section
        assert "wind electricity output" in section
        assert "No supported claims" not in section


def test_report_shortens_summary_when_only_one_claim_is_supported(tmp_path):
    state = run(tmp_path, adapter=SecondPassFixture(), budget=BudgetLimits(max_research_passes=1))
    markdown = render_report(state)
    assert len(state["report_claims"]) == 1
    assert "Only one supported summary claim is available" in markdown
    summary = markdown.split("## Summary\n\n", 1)[1].split("## Key Findings", 1)[0]
    assert "wind speed" not in summary
    assert "Unmet task criterion" in markdown
