"""User-requested report exports; internal context, logs and checkpoints stay private."""

import json

from evidenceforge.evidence.deduplication import WorkingEvidence, working_evidence
from evidenceforge.evidence.projection import audit, project
from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.services.observability import public_progress
from evidenceforge.services.usage import usage_summary


def report_export(state: ResearchState) -> str:
    s = StateSnapshot.model_validate(state)
    if s.run_status.value in {"created", "running"}:
        raise ValueError("Report export requires a finalized run.")
    deduplication_enabled = any(e.kind == "working_evidence_enabled" for e in s.events.values())
    working = (
        working_evidence(s.evidence_store.values())
        if deduplication_enabled
        else WorkingEvidence(evidence=tuple(s.evidence_store.values()), duplicates=())
    )
    data = {
        "export_version": 1,
        "run_id": s.run_id,
        "thread_id": s.thread_id,
        "progress": public_progress(state).as_dict(),
        "evidence_mode": (
            "live_sources_and_documents" if s.request.document_ids else "live_sources"
        )
        if any(e.kind == "live_retrieval" for e in s.events.values())
        else ("local_documents" if s.request.document_ids else "synthetic_fixture"),
        "model": next(
            (e.message for e in s.events.values() if e.kind == "gemini_model"), "offline_fixture"
        ),
        "questions": [q.model_dump(mode="json") for q in s.research_questions],
        "report": s.final_report.model_dump(mode="json") if s.final_report else None,
        "graph": project(state).model_dump(mode="json"),
        "audit": audit(state),
        "deduplication": {
            "applied_to_model_input": deduplication_enabled,
            "retained_passages": len(s.evidence_store),
            "working_passages": len(working.evidence),
            "duplicates": [d.model_dump(mode="json") for d in working.duplicates],
            "limitation": "Literal copies/containment do not establish independent corroboration.",
        },
        "usage": usage_summary(state),
        "limitations": [
            "Exact passage checks do not independently establish source truth.",
            "Export contains selected source and document passages.",
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
