"""Conservative finalization and Markdown delivery of audited fixture quotations."""

import html
import re
from typing import cast

from pydantic import JsonValue

from evidenceforge.evidence.deduplication import working_evidence
from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.identity import stable_id
from evidenceforge.nodes.common import Update, checked_patch, record_data
from evidenceforge.nodes.quality import quality_remaining
from evidenceforge.nodes.quality_common import quality_event
from evidenceforge.schemas import Report, ReportSection, utc_now


def finalize(state: ResearchState) -> Update:
    s = StateSnapshot.model_validate(state)
    if s.run_status != "running":
        return {}
    accepted = {
        a.claim_id for a in s.citation_audit if a.structural_valid and a.support == "supported"
    }
    claims = {cid: c for cid, c in s.report_claims.items() if cid in accepted}
    blocked = [a for a in s.citation_audit if a.claim_id not in accepted]
    approved = s.critic_verdict is not None and s.critic_verdict.decision == "approved"
    complete = (
        bool(claims)
        and not blocked
        and approved
        and s.coverage_status == "sufficient"
        and not s.stage_error
    )
    reason = s.stop_reason.value if s.stop_reason else "no_evidence"
    if complete:
        status, reason = "completed", "sufficient"
    elif claims:
        status = "partial"
        if blocked or not approved:
            reason = "model_call_limit" if quality_remaining(s) < 2 else "rewrite_limit"
        if s.stage_error:
            reason = s.stop_reason.value if s.stop_reason else "fatal_error"
    else:
        status = "failed" if s.stage_error else "insufficient_evidence"
        if not s.evidence_store:
            reason = "fatal_error" if s.stage_error else "no_evidence"
        elif blocked or not approved:
            reason = "model_call_limit" if quality_remaining(s) < 2 else "rewrite_limit"
    if s.stage_error:
        reason = s.stop_reason.value if s.stop_reason else "fatal_error"
    report = None
    if s.draft_report and claims:
        report = Report(
            id=stable_id(
                "final_report",
                s.run_id,
                s.draft_report.draft_version,
                cast(JsonValue, sorted(claims)),
            ),
            draft_version=s.draft_report.draft_version,
            sections=tuple(
                ReportSection(
                    name=section.name,
                    claim_ids=tuple(cid for cid in section.claim_ids if cid in claims),
                )
                for section in s.draft_report.sections
            ),
            source_ids=tuple(
                sorted(
                    {
                        s.evidence_store[eid].source_id
                        for c in claims.values()
                        for eid in c.evidence_ids
                    }
                )
            ),
        )
    return checked_patch(
        state,
        {
            "report_claims": {cid: record_data(c) for cid, c in claims.items()},
            "claim_evidence_map": {
                lid: record_data(link)
                for lid, link in s.claim_evidence_map.items()
                if link.claim_id in claims
            },
            "draft_report": record_data(report) if report else None,
            "final_report": record_data(report) if report else None,
            "critic_verdict": record_data(s.critic_verdict)
            if report and s.critic_verdict
            else None,
            "citation_audit": [record_data(a) for a in s.citation_audit if a.claim_id in claims],
            "unresolved_audits": [record_data(a) for a in blocked],
            "run_status": status,
            "stop_reason": reason,
            "finished_at": utc_now().isoformat(),
            **quality_event(
                state,
                "finalizer",
                "Finalized the audited report with explicit limits and stop reason.",
            ),
        },
    )


def escape(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", html.escape(text, quote=True)).replace(
        "\n", " "
    )


def render_report(state: ResearchState) -> str:
    s = StateSnapshot.model_validate(state)
    has_documents = any(source.source_type == "document" for source in s.source_records.values())
    notice = (
        "**Offline fixture reasoning over local document passages.** These quotations "
        "come from supplied files; the workflow does not independently verify their truth."
        if has_documents
        else "**Offline synthetic fixture demonstration.** These passages are examples, "
        "not real measurements or a verified research answer."
    )
    live_models = [event.message for event in s.events.values() if event.kind == "gemini_model"]
    if live_models:
        notice = (
            f"**Live Gemini reasoning (`{escape(live_models[0])}`).** "
            + (
                "Evidence comes from supplied local documents."
                if has_documents
                else "Evidence comes from synthetic fixtures, not real measurements."
            )
            + " Retained quotations are checked; source truth is not independently verified."
        )
    if any(event.kind == "live_retrieval" for event in s.events.values()):
        notice = (
            f"**Live retrieval with {'Gemini' if live_models else 'offline fixture'} reasoning.** "
            "Evidence comes from explicitly selected live sources and any selected documents. "
            "Retained quotations are checked; source truth is not independently verified."
        )
    lines = [
        "# EvidenceForge research report",
        "",
        notice,
        "",
        f"Status: `{s.run_status.value}` | "
        f"Stop: `{s.stop_reason.value if s.stop_reason else 'unfinished'}` | "
        f"Retrieval passes: {s.iteration_count} | Rewrites: {s.revision_count}",
        "",
    ]
    report = s.final_report
    sources = {sid: index + 1 for index, sid in enumerate(report.source_ids if report else ())}
    sections = {section.name: section.claim_ids for section in report.sections} if report else {}
    for name, title in (
        ("summary", "Summary"),
        ("key_findings", "Key Findings"),
        ("limitations", "Quoted Limitations"),
        ("disagreements", "Quoted Disagreements"),
    ):
        if name not in ("summary", "key_findings") and not sections.get(name):
            continue
        lines.extend([f"## {title}", ""])
        rendered: list[str] = []
        for cid in sections.get(name, ()):
            claim = s.report_claims[cid]
            citations = sorted(
                {sources[s.evidence_store[eid].source_id] for eid in claim.evidence_ids}
            )
            locations = []
            for eid in claim.evidence_ids:
                locator = s.evidence_store[eid].locator
                if locator.page is not None:
                    locations.append(f"page {locator.page}")
                if locator.paragraph is not None:
                    locations.append(f"paragraph {locator.paragraph}")
                if locator.section is not None:
                    locations.append(escape(locator.section))
            suffix = " (" + "; ".join(sorted(set(locations))) + ")" if locations else ""
            rendered.append(
                f'"{escape(claim.statement)}" ' + " ".join(f"[{n}]" for n in citations) + suffix
            )
        if name == "summary" and rendered:
            count = min(3, len(rendered))
            for index in range(count):
                start, end = index * len(rendered) // count, (index + 1) * len(rendered) // count
                lines.extend([" ".join(rendered[start:end]), ""])
            if count < 2:
                lines.append(
                    "Only one supported summary claim is available; the summary is shortened."
                )
        else:
            lines.extend("- " + value for value in rendered)
        if not sections.get(name):
            lines.append("No supported claims are available for this section.")
        lines.append("")
    lines.extend(["## Sources", ""])
    for sid, index in sources.items():
        source = s.source_records[sid]
        url = str(source.url).replace("(", "%28").replace(")", "%29") if source.url else None
        title = escape(source.title)
        lines.append(f"- [{index}] [{title}]({url})" if url else f"- [{index}] {title}")
        if source.document_id is not None:
            dates = sorted(
                {
                    a.retrieved_at.isoformat()
                    for a in s.source_acquisitions.values()
                    if a.source_id == sid
                }
            )
            lines.append(
                f"  Document: `{source.document_id}`; "
                f"SHA-256: `{source.document_hash}`; retrieved: " + ", ".join(dates)
            )
        used_evidence = sorted(
            {
                eid
                for claim in s.report_claims.values()
                for eid in claim.evidence_ids
                if s.evidence_store[eid].source_id == sid
            }
        )
        for eid in used_evidence:
            evidence = s.evidence_store[eid]
            locator = evidence.locator
            location = [f"offsets {locator.start_offset}-{locator.end_offset}"]
            if locator.page is not None:
                location.append(f"page {locator.page}")
            if locator.paragraph is not None:
                location.append(f"paragraph {locator.paragraph}")
            lines.append(
                f'  - Evidence `{eid}`: "{escape(evidence.passage)}" '
                + "("
                + "; ".join(location)
                + ")."
            )
    if not sources:
        lines.append("No retained sources support a final claim.")
    lines.extend(
        [
            "",
            "## Limitations and unresolved work",
            "",
            "Citation checks verify exact retained quotations and source snapshots. "
            + (
                "Gemini assesses coverage; evidence admission still uses lexical matching. "
                "Neither check independently establishes source truth."
                if live_models
                else "Fixture coverage uses lexical matching; neither check independently "
                "establishes source truth."
            ),
        ]
    )
    duplicates = working_evidence(s.evidence_store.values()).duplicates
    if duplicates and any(e.kind == "working_evidence_enabled" for e in s.events.values()):
        lines.append(
            f"{len(duplicates)} literal duplicate/contained passages were grouped for model input. "
            "Original source spans remain retained; copies do not establish "
            "independent corroboration."
        )
    comparisons = [
        c for c in s.comparisons.values() if c.relationship in {"contradicts", "not_comparable"}
    ]
    if comparisons:
        lines.extend(
            [
                "",
                "## Evidence comparison audit",
                "",
                "Comparisons concern retained numeric statements; source truth remains unverified.",
                "",
            ]
        )
        for c in sorted(comparisons, key=lambda c: c.id):
            lines.append(f"- `{c.relationship}`: {escape(c.rationale)}")
            for pid in (c.left_id, c.right_id):
                p = s.propositions[pid]
                e = s.evidence_store[p.evidence_id]
                source = s.source_records[e.source_id]
                url = (
                    str(source.url).replace("(", "%28").replace(")", "%29") if source.url else None
                )
                ref = f"[{escape(source.title)}]({url})" if url else escape(source.title)
                comparison_location = (
                    f"; page {e.locator.page}"
                    if e.locator.page
                    else f"; paragraph {e.locator.paragraph}"
                    if e.locator.paragraph
                    else ""
                )
                lines.append(
                    f'  - "{escape(p.quote)}" - {ref}{comparison_location}; evidence: `{e.id}`'
                )
    for gap in s.gaps:
        lines.append(f"- Unmet task criterion: {escape(gap.missing_aspect)}")
    if s.unresolved_audits:
        lines.append(f"- Omitted {len(s.unresolved_audits)} claims that failed citation checks.")
    if s.critic_verdict and s.critic_verdict.decision != "approved":
        lines.append("- The critic still requested revisions when the workflow stopped.")
    if s.stage_error or s.run_status == "failed":
        lines.append(
            "- A workflow stage failed; inspect the sanitized error records in the saved JSON."
        )
    return "\n".join(lines) + "\n"
