"""Capture synthetic research runs and build an offline, inspectable demo replay."""

import argparse
import asyncio
import html
import json
from pathlib import Path

from evidenceforge.evidence.projection import project
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.research import ReportDraft, SynthesisInput
from evidenceforge.retrieval.fixtures import DisputeFixture, SecondPassFixture
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType, utc_now
from evidenceforge.services.research import ResearchService, atomic_write
from evidenceforge.services.retrieval import RetrievalService

QUESTION = "Compare solar and wind electricity output."
BAD_STATEMENT = "Synthetic injected unsupported claim: solar output is 999 GW everywhere."


class RepairDemoModel(FixtureResearchModel):
    """Deliberately inject one unsupported first draft; use normal quote synthesis next."""

    def __init__(self) -> None:
        super().__init__()
        self.observed_drafts: list[dict[str, object]] = []

    async def synthesize(self, request: SynthesisInput) -> object:
        draft = ReportDraft.model_validate(await super().synthesize(request))
        if self.synthesis_calls == 1:
            claims = list(draft.claims)
            claims[0] = claims[0].model_copy(update={"statement": BAD_STATEMENT})
            draft = ReportDraft(claims=tuple(claims))
        self.observed_drafts.append(
            {
                "draft_version": request.draft_version,
                "statements": [claim.statement for claim in draft.claims],
            }
        )
        return draft.model_dump(mode="json")


async def prepare(directory: Path) -> dict[str, object]:
    directory.mkdir(parents=True, exist_ok=True)
    sections: list[str] = []
    records: list[dict[str, object]] = []
    for name in ("coverage-loop", "dispute", "audit-repair", "partial-result"):
        case_dir = directory / name
        model = RepairDemoModel() if name == "audit-repair" else FixtureResearchModel()
        adapter = DisputeFixture() if name == "dispute" else SecondPassFixture()
        retrieval = (
            None
            if name == "audit-repair"
            else RetrievalService(case_dir, {SourceType.WEB: adapter})
        )
        service = ResearchService(case_dir, model=model, retrieval=retrieval)
        budget = BudgetLimits(max_research_passes=1 if name == "partial-result" else 3)
        question = (
            "What was Northfield solar electricity output?" if name == "dispute" else QUESTION
        )
        state = await service.run(ResearchRequest(question=question), budget)
        if name == "coverage-loop":
            assert state["run_status"] == "completed" and state["iteration_count"] == 2
        elif name == "dispute":
            assert state["run_status"] == "partial"
            assert any(c["relationship"] == "contradicts" for c in state["comparisons"].values())
        elif name == "audit-repair":
            assert state["run_status"] == "completed" and state["revision_count"] == 1
            assert isinstance(model, RepairDemoModel)
            assert model.synthesis_calls == model.critic_calls == 2
            assert BAD_STATEMENT not in service.report_path(state).read_text(encoding="utf-8")
            atomic_write(
                case_dir / "scripted-drafts.json", json.dumps(model.observed_drafts, indent=2)
            )
        else:
            assert state["run_status"] == "partial" and state["stop_reason"] == "pass_limit"
            assert state["gaps"]
        report_dir = service.report_path(state).parent
        relative = report_dir.relative_to(directory).as_posix()
        record = {
            "scenario": name,
            "run_id": state["run_id"],
            "status": state["run_status"],
            "stop": state["stop_reason"],
            "passes": state["iteration_count"],
            "rewrites": state["revision_count"],
            "report": relative + "/report.md",
            "state": relative + "/state.json",
            "claims": len(state["report_claims"]),
        }
        records.append(record)
        parts = [
            f'<section id="{name}"><h2>{html.escape(name.replace("-", " ").title())}</h2>',
            '<p class="label">Captured offline synthetic run</p>',
            f"<p>Status: <b>{record['status']}</b> · stop: {record['stop']} · "
            f"passes: {record['passes']} · rewrites: {record['rewrites']}</p>",
            f'<p><a href="{relative}/report.md">Report</a> · '
            f'<a href="{relative}/state.json">State</a> · '
            f'<a href="{relative}/audit.json">Audit</a> · '
            f'<a href="{relative}/graph.json">Graph</a></p>',
        ]
        if name == "audit-repair":
            parts.append(
                "<p>The harness deliberately supplied one unsupported first draft. "
                "The real citation checker requested a rewrite; the final report "
                "contains supported retained quotations.</p>"
                f"<details><summary>Show injected first draft</summary><p>"
                f"{html.escape(BAD_STATEMENT)}</p></details>"
                f'<p><a href="{name}/scripted-drafts.json">Observed draft sequence</a></p>'
            )
        for claim_id, claim in state["report_claims"].items():
            graph = project(state, claim_id)
            atomic_write(report_dir / f"{claim_id}.json", graph.model_dump_json(indent=2))
            parts.append("<details><summary>" + html.escape(str(claim["statement"])) + "</summary>")
            for evidence_id in claim["evidence_ids"]:
                evidence = state["evidence_store"][evidence_id]
                source = state["source_records"][evidence["source_id"]]
                parts.append(
                    "<blockquote>" + html.escape(evidence["passage"]) + "</blockquote>"
                    "<p>Source: "
                    + html.escape(source["title"])
                    + "</p><pre>"
                    + html.escape(json.dumps(evidence["locator"], indent=2))
                    + "</pre>"
                )
            parts.append(
                f'<a href="{relative}/{claim_id}.json">Selected claim support graph</a></details>'
            )
        for comparison in state["comparisons"].values():
            if comparison["relationship"] in {"contradicts", "not_comparable"}:
                parts.append(
                    "<p><b>"
                    + html.escape(comparison["relationship"])
                    + "</b>: "
                    + html.escape(comparison["rationale"])
                    + "</p>"
                )
        for gap in state["gaps"]:
            parts.append("<p>Unresolved criterion: " + html.escape(gap["missing_aspect"]) + "</p>")
        parts.append("</section>")
        sections.append("\n".join(parts))
    manifest = {
        "mode": "offline_synthetic_replay",
        "generated_at": utc_now().isoformat(),
        "provider_calls": 0,
        "runs": records,
        "index": str((directory / "index.html").resolve()),
    }
    atomic_write(directory / "manifest.json", json.dumps(manifest, indent=2))
    page = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EvidenceForge synthetic demo replay</title>
<style>body{font:16px/1.6 system-ui;max-width:1000px;margin:36px auto;padding:0 24px;
background:#f4f7fa;color:#172534}a{color:#075baf}section{background:white;padding:24px;
margin:24px 0;border:1px solid #d3dce5;border-radius:12px}.label{color:#614300;
background:#fff0c5;padding:8px}summary{cursor:pointer;padding:12px}details{border:1px solid
#ddd;margin:12px 0;padding:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere}
blockquote{border-left:3px solid #1d779e;margin:12px;padding:12px}</style>
<h1>EvidenceForge: inspect the evidence</h1>
<p class="label">OFFLINE SYNTHETIC REPLAY. Generated from actual local service runs.
No model or search provider calls. Demonstrates mechanics, not verified research accuracy.</p>
<nav><a href="#coverage-loop">Coverage loop</a> · <a href="#dispute">Dispute</a> ·
<a href="#audit-repair">Audit repair</a> · <a href="#partial-result">Partial result</a></nav>
<p>Click a finding to inspect its retained passage, source and locator.
Fixture source URLs are placeholders. Local graph links provide the retained support.</p>
"""
    atomic_write(directory / "index.html", page + "\n".join(sections) + "</html>\n")
    print(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".evidenceforge/demo/phase11"))
    asyncio.run(prepare(parser.parse_args().data_dir))
