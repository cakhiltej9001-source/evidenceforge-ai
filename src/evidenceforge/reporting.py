"""Conservative finalization and Markdown delivery of audited fixture quotations."""

import html
import re
from typing import cast

from pydantic import JsonValue

from evidenceforge.answering import answer_excerpts, unresolved_answer
from evidenceforge.evidence.deduplication import working_evidence
from evidenceforge.evidence.text_quality import (
    EXERCISE,
    absence_supported,
    aligned_table,
    ambiguous_flat_table,
)
from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.identity import stable_id
from evidenceforge.nodes.common import Update, checked_patch, record_data
from evidenceforge.nodes.extraction import ambiguous_table
from evidenceforge.nodes.quality import quality_remaining
from evidenceforge.nodes.quality_common import quality_event
from evidenceforge.schemas import (
    EvidenceItem,
    QuestionCoverage,
    QuestionCoverageStatus,
    Report,
    ReportSection,
    ResearchGap,
    SourceType,
    utc_now,
)

OCR_TRANSCRIPT_LIMITATION = (
    "Local OCR evidence is a machine-generated transcript. Quotation checks and offsets "
    "refer to that transcript; verify wording, numbers and layout against the original "
    "PDF page image."
)


def ocr_transcripts(snapshot: StateSnapshot) -> tuple[EvidenceItem, ...]:
    """Identify retained OCR passages from their immutable document locators."""
    return tuple(
        sorted(
            (
                evidence
                for evidence in snapshot.evidence_store.values()
                if evidence.locator.section == "local OCR transcription"
                and evidence.source_id in snapshot.source_records
                and snapshot.source_records[evidence.source_id].source_type == SourceType.DOCUMENT
            ),
            key=lambda evidence: evidence.id,
        )
    )


def finalize(state: ResearchState) -> Update:
    s = StateSnapshot.model_validate(state)
    if s.run_status != "running":
        return {}
    accepted = {
        a.claim_id for a in s.citation_audit if a.structural_valid and a.support == "supported"
    }
    claims = {cid: c for cid, c in s.report_claims.items() if cid in accepted}
    quality_gaps = []
    strict = any(e.kind == "report_quality_guard_v2" for e in s.events.values())
    guarded = strict or any(e.kind == "report_quality_guard" for e in s.events.values())
    if guarded:
        for cid, claim in tuple(claims.items()):
            if (
                (ambiguous_flat_table(claim.statement) or EXERCISE.search(claim.statement))
                if strict
                else ambiguous_table(claim.statement)
                or re.search(
                    r"\b(?:Problem|Question|Exercise)\s+\d+\s*[-:.\u2013\u2014]", claim.statement
                )
            ):
                del claims[cid]
                for qid in claim.question_ids:
                    quality_gaps.append(
                        ResearchGap(
                            id=stable_id("report_quality_gap", s.run_id, cid, qid),
                            question_id=qid,
                            missing_aspect=(
                                "An ambiguous numeric table or exercise quotation was omitted. "
                                "Recover aligned rows or prose before interpreting values."
                            ),
                            needed_source_types=(SourceType.WEB, SourceType.DOCUMENT),
                            recommended_query="Find aligned rows or relevant prose.",
                        )
                    )
        for question in s.research_questions:
            for index, criterion in enumerate(question.acceptance_criteria):
                if not re.search(
                    r"\b(?:missing|unavailable|absent|unreported|not provided|not reported)\b",
                    criterion,
                    re.I,
                ):
                    continue
                if strict and absence_supported(
                    criterion,
                    (c.statement for c in claims.values() if question.id in c.question_ids),
                ):
                    continue
                if not strict and any(
                    question.id in c.question_ids
                    and re.search(
                        r"\b(?:missing|unavailable|absent|unreported|not provided|not reported)\b",
                        c.statement,
                        re.I,
                    )
                    for c in claims.values()
                ):
                    continue
                quality_gaps.append(
                    ResearchGap(
                        id=stable_id("report_quality_gap", s.run_id, question.id, index),
                        question_id=question.id,
                        missing_aspect=(
                            "The final quotations do not establish the requested "
                            "missing-data inventory: " + criterion
                        ),
                        needed_source_types=(SourceType.WEB, SourceType.DOCUMENT),
                        recommended_query="Find reporting scope and missing-data information.",
                    )
                )
    blocked = [a for a in s.citation_audit if a.claim_id not in accepted]
    approved = s.critic_verdict is not None and s.critic_verdict.decision == "approved"
    complete = (
        bool(claims)
        and not blocked
        and approved
        and s.coverage_status == "sufficient"
        and not s.stage_error
        and not quality_gaps
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
    if quality_gaps and not s.stage_error:
        reason = "no_progress" if reason == "sufficient" else reason
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
            **(
                {
                    "gaps": [record_data(g) for g in (*s.gaps, *quality_gaps)],
                    "coverage_status": "missing",
                    "coverage_by_question": {
                        qid: record_data(
                            QuestionCoverage(
                                question_id=qid,
                                status=QuestionCoverageStatus.PARTIAL,
                                evidence_ids=coverage.evidence_ids,
                                rationale="Final report checks left a criterion unresolved.",
                            )
                        )
                        if any(g.question_id == qid for g in quality_gaps)
                        else record_data(coverage)
                        for qid, coverage in s.coverage_by_question.items()
                    },
                }
                if quality_gaps
                else {}
            ),
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


def retained_source_passages(snapshot: StateSnapshot, source_id: str) -> tuple[EvidenceItem, ...]:
    """Read only the retained passages actually cited by this finalized report."""
    report = snapshot.final_report
    if report is None or source_id not in report.source_ids:
        return ()
    evidence_ids = {
        eid
        for section in report.sections
        for cid in section.claim_ids
        for eid in snapshot.report_claims[cid].evidence_ids
        if snapshot.evidence_store[eid].source_id == source_id
    }
    return tuple(
        sorted(
            (snapshot.evidence_store[eid] for eid in evidence_ids),
            key=lambda item: (item.locator.page or 0, item.locator.start_offset, item.id),
        )
    )


def retained_source_text(snapshot: StateSnapshot, source_id: str) -> str:
    """Download saved quotations without fetching or mirroring the original website."""
    passages = retained_source_passages(snapshot, source_id)
    if not passages:
        return "No cited passages are available for this source.\n"
    source = snapshot.source_records[source_id]
    acquisitions = {aid for evidence in passages for aid in evidence.acquisition_ids}
    dates = sorted(
        snapshot.source_acquisitions[aid].retrieved_at.isoformat() for aid in acquisitions
    )
    scopes = sorted({snapshot.source_acquisitions[aid].content_scope for aid in acquisitions})
    lines = [
        "Saved source passages - retained evidence, not a full-page mirror",
        source.title,
        "Original URL: " + (str(source.url) if source.url else "Local document"),
        "Provider: " + source.provider,
        "Retrieved: " + ", ".join(dict.fromkeys(dates)),
        "Retained content scope: " + ", ".join(scopes),
        "Original website access and source truth are not verified by this download.",
        "",
    ]
    for index, evidence in enumerate(passages, 1):
        locator = evidence.locator
        location = [f"offsets {locator.start_offset}-{locator.end_offset}"]
        if locator.page is not None:
            location.append(f"page {locator.page}")
        if locator.paragraph is not None:
            location.append(f"paragraph {locator.paragraph}")
        if locator.section is not None:
            location.append(locator.section)
        lines.extend([f"Passage {index} (" + "; ".join(location) + ")", evidence.passage, ""])
    return "\n".join(lines)


def render_report(
    state: ResearchState, *, local_source_links: bool = False, answer_first: bool = False
) -> str:
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
    public_sources = {
        source.id
        for source in s.source_records.values()
        if source.source_type in {SourceType.WEB, SourceType.API, SourceType.MCP}
        and source.provider != "fixture"
        and source.owner_scope is None
        and source.url is not None
        and source.access_status in {"available", "excerpt_only"}
    }
    if public_sources:
        if any(event.kind == "live_retrieval" for event in s.events.values()):
            heading = (
                f"**Live retrieval with {'Gemini' if live_models else 'offline fixture'} "
                "reasoning.** "
            )
        elif live_models:
            heading = f"**Live Gemini reasoning (`{escape(live_models[0])}`).** "
        else:
            heading = "**Offline fixture reasoning over retained public source snapshots.** "
        origins = ["retained public source snapshots"]
        if has_documents:
            origins.append("supplied local documents")
        if any(
            source.provider == "fixture" or source.source_type == SourceType.FIXTURE
            for source in s.source_records.values()
        ):
            origins.append("synthetic fixtures")
        notice = (
            heading
            + "Evidence comes from "
            + " and ".join(origins)
            + ". Retained quotations are checked; source truth is not independently verified."
        )
        if any(
            s.source_records[sid].access_status == "excerpt_only" for sid in public_sources
        ) or any(
            acquisition.source_id in public_sources
            and (acquisition.content_scope == "search_excerpt" or acquisition.section is not None)
            for acquisition in s.source_acquisitions.values()
        ):
            notice += (
                " Some retained material consists of search or section excerpts; "
                "this run does not establish full-page coverage for those sources."
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
    for event in s.events.values():
        if event.kind.startswith("input_review_") and event.kind != "input_review_research":
            lines.extend(["Input guidance: " + escape(event.message), ""])
    report = s.final_report
    sources = {sid: index + 1 for index, sid in enumerate(report.source_ids if report else ())}
    sections = {section.name: section.claim_ids for section in report.sections} if report else {}
    readable = any(event.kind == "readable_report" for event in s.events.values())
    quote_numbers = {cid: index + 1 for index, cid in enumerate(s.report_claims)}
    shown: dict[str, int] = {}
    if readable and sections.get("summary"):
        assigned = {cid for name, ids in sections.items() if name != "summary" for cid in ids}
        sections["key_findings"] = tuple(
            dict.fromkeys(
                (
                    *sections.get("key_findings", ()),
                    *(cid for cid in sections["summary"] if cid not in assigned),
                )
            )
        )
    if answer_first:
        # Summary selections remain findings even when replacing the summary's presentation.
        sections["key_findings"] = tuple(
            dict.fromkeys((*sections.get("key_findings", ()), *sections.get("summary", ())))
        )
        lines.extend(["## Answer", ""])
        if unresolved_answer(s):
            lines.extend(
                [
                    "The retained evidence contains unresolved differences or measurement "
                    "scopes. A single answer is not established; see the findings below.",
                    "",
                ]
            )
        else:
            excerpts = answer_excerpts(s)
            if excerpts:
                if s.run_status != "completed" or s.coverage_status != "sufficient":
                    lines.extend(
                        [
                            "The evidence is incomplete. These cited excerpts "
                            "give a partial answer.",
                            "",
                        ]
                    )
                for excerpt in excerpts:
                    source_id = s.evidence_store[excerpt.evidence_id].source_id
                    number = sources[source_id]
                    ref = (
                        f"[{number}](#saved-source-{number})"
                        if local_source_links
                        else f"[{number}]"
                    )
                    lines.extend([escape(excerpt.text) + " " + ref, ""])
                lines.extend(
                    ["Short quotations from the retained evidence; full passages follow.", ""]
                )
            else:
                lines.extend(
                    [
                        "A concise supported answer could not be extracted from the retained "
                        "quotations. Review the findings and unresolved criteria below.",
                        "",
                    ]
                )
    for name, title in (
        ("summary", "Summary"),
        ("key_findings", "Key Findings"),
        ("limitations", "Quoted Limitations"),
        ("disagreements", "Quoted Disagreements"),
    ):
        if answer_first and name == "summary":
            continue
        if name not in ("summary", "key_findings") and not sections.get(name):
            continue
        lines.extend([f"## {title}", ""])
        if readable and name == "disagreements":
            lines.extend(
                [
                    "These source differences remain unresolved. Retained evidence does not "
                    "establish whether they reflect dates, measurement scope, rounding or error. "
                    "Do not assume the values are directly comparable or choose one as correct.",
                    "",
                ]
            )
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
            refs = " ".join(
                f"[{n}](#saved-source-{n})" if local_source_links else f"[{n}]" for n in citations
            )
            if readable and name == "summary":
                rendered.append(f"Supported quotation Q{quote_numbers[cid]}: {refs}{suffix}")
            elif readable and claim.statement in shown:
                rendered.append(f"See quotation Q{shown[claim.statement]} above. {refs}{suffix}")
            elif any(
                e.kind == "report_quality_guard_v2" for e in s.events.values()
            ) and aligned_table(claim.statement):
                longest = max(
                    (len(m.group()) for m in re.finditer(chr(96) + "+", claim.statement)), default=0
                )
                fence = chr(96) * max(3, longest + 1)
                rendered.append(
                    f"**Q{quote_numbers[cid]}.** {refs}{suffix}\n\n"
                    f"{fence}text\n{claim.statement}\n{fence}"
                )
                shown[claim.statement] = quote_numbers[cid]
            else:
                label = f"**Q{quote_numbers[cid]}.** " if readable else ""
                rendered.append(label + f'"{escape(claim.statement)}" ' + refs + suffix)
                shown[claim.statement] = quote_numbers[cid]
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
    if sources:
        lines.extend(
            [
                (
                    "Source titles open saved passages below. Original website links are "
                    "separate; those sites may block access with HTTP 403."
                    if local_source_links
                    else "Original websites control access and may return HTTP 403. "
                    "Saved quoted passages are available in the app and the JSON download."
                ),
                "",
            ]
        )
    for sid, index in sources.items():
        source = s.source_records[sid]
        url = str(source.url).replace("(", "%28").replace(")", "%29") if source.url else None
        title = escape(source.title)
        if local_source_links:
            line = f"- [{index}] [{title}](#saved-source-{index})"
            if url:
                line += f" — [Original website]({url})"
            lines.append(line)
        else:
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
            if locator.section is not None:
                location.append(escape(locator.section))
            prefix = f"  - Evidence `{eid}`: "
            quote = "" if readable else f'"{escape(evidence.passage)}" '
            lines.append(prefix + quote + "(" + "; ".join(location) + ").")
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
    if readable:
        lines.extend(
            [
                "",
                "Passages use complete sentence boundaries when available. Upstream excerpts "
                "may already be incomplete. Full retained text and exact offsets are available "
                "in the JSON export; repeated quotations are referenced once in this report.",
            ]
        )
        if len(sources) > 1 and any(
            re.search(r"\d+(?:\.\d+)?\s*(?:%|\bpercent\b)", c.statement, re.I)
            for c in s.report_claims.values()
        ):
            lines.append(
                "Quoted percentages have not been reconciled across source dates and "
                "measurement scopes unless the evidence comparison audit explicitly says so. "
                "Differing values remain unresolved; quotation checks do not select a winner."
            )
    if any(
        e.kind in {"report_quality_guard", "report_quality_guard_v2"} for e in s.events.values()
    ):
        lines.append(
            "Ambiguous flattened numeric tables and exercise instructions are excluded. "
            "Missing-data criteria need explicit reporting evidence; absence from a search "
            "excerpt does not establish absence from the source. These conservative checks "
            "do not establish general semantic completeness."
        )
    if ocr_transcripts(s):
        lines.extend(["", OCR_TRANSCRIPT_LIMITATION])
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
