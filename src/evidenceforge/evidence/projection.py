"""Deterministic projections of authoritative records; JSON and accessible tables."""

from evidenceforge.evidence.contracts import EvidenceGraph, GraphEdge, GraphNode
from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.identity import stable_id
from evidenceforge.reporting import escape


def project(state: ResearchState, claim_id: str | None = None) -> EvidenceGraph:
    s = StateSnapshot.model_validate(state)
    if claim_id is not None and claim_id not in s.report_claims:
        raise ValueError("Unknown claim ID.")
    nodes = []
    for kind, records, field in (
        ("question", {q.id: q for q in s.research_questions}, "question"),
        ("claim", s.report_claims, "statement"),
        ("evidence", s.evidence_store, "passage"),
        ("source", s.source_records, "title"),
    ):
        for rid in sorted(records):
            data = records[rid].model_dump(mode="json")
            nodes.append(
                GraphNode.model_validate(dict(id=rid, kind=kind, label=data[field], record=data))
            )
    edges: dict[str, GraphEdge] = {}

    def edge(
        source: str, target: str, relationship: str, rationale: str, record_id: str | None = None
    ) -> None:
        e = GraphEdge.model_validate(
            dict(
                id=stable_id("edge", source, target, relationship, record_id),
                source=source,
                target=target,
                relationship=relationship,
                rationale=rationale,
                record_id=record_id,
            )
        )
        edges[e.id] = e

    for c in s.report_claims.values():
        for qid in c.question_ids:
            edge(c.id, qid, "addresses", "Claim was assigned to this research question.")
    for e in s.evidence_store.values():
        edge(e.id, e.source_id, "retrieved_from", "Exact retained passage and source version.")
        for qid in e.question_ids:
            edge(e.id, qid, "addresses", e.relevance_rationale)
    for link in s.claim_evidence_map.values():
        relationship = (
            "contextualizes" if link.relationship == "context" else link.relationship.value
        )
        edge(link.evidence_id, link.claim_id, relationship, link.rationale, link.id)
    for comparison in s.comparisons.values():
        left = s.propositions[comparison.left_id].evidence_id
        right = s.propositions[comparison.right_id].evidence_id
        relationship = {
            "supports": "supports",
            "contradicts": "contradicts",
            "duplicate": "duplicate_of",
            "not_comparable": "contextualizes",
        }[comparison.relationship]
        edge(left, right, relationship, comparison.rationale, comparison.id)
    groups: dict[str, list[str]] = {}
    for sid, quality in s.source_quality.items():
        groups.setdefault(quality.family_group, []).append(sid)
    for members in groups.values():
        canonical = min(members)
        for sid in sorted(members):
            if sid != canonical:
                edge(
                    sid,
                    canonical,
                    "duplicate_of",
                    "Same family or retained content; independent votes are not established.",
                )
    gaps = s.gaps
    if claim_id is not None:
        included = {claim_id}
        included.update(e.source for e in edges.values() if e.target == claim_id)
        included.update(e.target for e in edges.values() if e.source == claim_id)
        evidence_ids = included & set(s.evidence_store)
        # Include all recorded disputes/context for the finding and their source locators.
        for graph_edge in edges.values():
            if graph_edge.record_id in s.comparisons and (
                graph_edge.source in evidence_ids or graph_edge.target in evidence_ids
            ):
                included.update((graph_edge.source, graph_edge.target))
        for eid in included & set(s.evidence_store):
            included.add(s.evidence_store[eid].source_id)
        nodes = [n for n in nodes if n.id in included]
        edges = {
            eid: e for eid, e in edges.items() if e.source in included and e.target in included
        }
        qids = set(s.report_claims[claim_id].question_ids)
        gaps = tuple(g for g in gaps if g.question_id in qids)
    return EvidenceGraph(
        run_id=s.run_id,
        owner_scope=s.owner_scope,
        draft_version=s.draft_report.draft_version if s.draft_report else 0,
        nodes=tuple(nodes),
        edges=tuple(edges[eid] for eid in sorted(edges)),
        gap_records=tuple(g.model_dump(mode="json") for g in gaps),
    )


def audit(state: ResearchState) -> dict[str, object]:
    s = StateSnapshot.model_validate(state)
    return {
        "version": "evidence_audit_v1",
        "run_id": s.run_id,
        "owner_scope": s.owner_scope,
        "analysis_signature": s.analysis_signature,
        "analysis_notes": list(s.analysis_notes),
        "analysis_limited": s.analysis_limited,
        "source_quality": {
            sid: q.model_dump(mode="json") for sid, q in sorted(s.source_quality.items())
        },
        "propositions": {
            pid: p.model_dump(mode="json") for pid, p in sorted(s.propositions.items())
        },
        "comparisons": {cid: c.model_dump(mode="json") for cid, c in sorted(s.comparisons.items())},
        "claim_evidence_links": {
            lid: link.model_dump(mode="json") for lid, link in sorted(s.claim_evidence_map.items())
        },
        "citation_audit": [a.model_dump(mode="json") for a in s.citation_audit],
        "unresolved_audits": [a.model_dump(mode="json") for a in s.unresolved_audits],
        "coverage": {
            qid: q.model_dump(mode="json") for qid, q in sorted(s.coverage_by_question.items())
        },
        "gaps": [g.model_dump(mode="json") for g in s.gaps],
    }


def render_inspection(state: ResearchState, claim_id: str | None = None) -> str:
    graph = project(state, claim_id)
    s = StateSnapshot.model_validate(state)
    by_id = {n.id: n for n in graph.nodes}
    lines = [
        "# Evidence inspection",
        "",
        "Exact retained quotations and heuristic judgments; rankings are not truth probabilities.",
        "",
        "| ID / kind | Retained record |",
        "|---|---|",
    ]
    for n in graph.nodes:
        location = ""
        if n.kind == "evidence":
            e = s.evidence_store[n.id]
            location = (
                f"; snapshot {e.locator.snapshot_id}; "
                f"offsets {e.locator.start_offset}:{e.locator.end_offset}"
            )
            if e.locator.page:
                location += f"; page {e.locator.page}"
            if e.locator.paragraph:
                location += f"; paragraph {e.locator.paragraph}"
            if e.locator.section:
                location += "; " + e.locator.section
        elif n.kind == "source":
            source = s.source_records[n.id]
            location = (
                "; "
                + (str(source.url) if source.url else str(source.document_id))
                + "; hash "
                + source.content_hash
            )
        lines.append(f"| {n.id} / {n.kind} | {escape(n.label + location)} |")
    lines.extend(["", "| From | Relationship | To | Rationale / record |", "|---|---|---|---|"])
    for graph_edge in graph.edges:
        lines.append(
            f"| {graph_edge.source} | {graph_edge.relationship} | {graph_edge.target} | "
            f"{escape(graph_edge.rationale)}; {graph_edge.record_id or 'derived'} |"
        )
    lines.extend(
        [
            "",
            "## Source ranking",
            "",
            "Unknown features use a neutral value of 0.5. "
            "Family copies do not count as independent votes.",
            "",
            "| Source | Heuristic score | Known weight | Features: value Ã— weight |",
            "|---|---|---|---|",
        ]
    )
    for sid, q in sorted(s.source_quality.items(), key=lambda x: (-x[1].score, x[0])):
        if sid not in by_id:
            continue
        features = "; ".join(
            f"{f.name}: {'unknown' if f.value is None else str(round(f.value, 3))} x {f.weight}"
            for f in q.features
        )
        lines.append(f"| {sid} | {q.score:.3f} | {q.observed_weight:.3f} | {features} |")
    lines.extend(["", "## Analysis limits", ""] + ["- " + escape(n) for n in s.analysis_notes])
    lines.extend(
        ["", "## Unresolved gaps", ""]
        + ["- " + escape(str(g["missing_aspect"])) for g in graph.gap_records]
    )
    return "\n".join(lines) + "\n"
