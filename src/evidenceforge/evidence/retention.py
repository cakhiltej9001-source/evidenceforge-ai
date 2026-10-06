"""Replace the lowest relevance passages while preserving cited evidence and snapshots."""

from langgraph.types import Overwrite

from evidenceforge.graph.reducers import RecordMap, merge_evidence
from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.identity import stable_id
from evidenceforge.nodes.common import record_data
from evidenceforge.schemas import EvidenceItem, RejectedEvidence


def select_evidence(
    state: ResearchState, incoming: RecordMap, rejected: RecordMap
) -> dict[str, object]:
    snapshot = StateSnapshot.model_validate(state)
    candidates = merge_evidence(state["evidence_store"], incoming)
    pinned = {eid for claim in snapshot.report_claims.values() for eid in claim.evidence_ids}
    parsed = {eid: EvidenceItem.model_validate(value) for eid, value in candidates.items()}
    ordered = sorted(
        candidates,
        key=lambda eid: (
            eid not in pinned,
            -parsed[eid].relevance,
            eid not in state["evidence_store"],
            eid,
        ),
    )
    selected: RecordMap = {}
    size = 0
    for eid in ordered:
        item = candidates[eid]
        needed = len(str(item["passage"]).encode("utf-8"))
        if (
            len(selected) < snapshot.budget.max_evidence_count
            and size + needed <= snapshot.budget.max_evidence_bytes
        ):
            selected[eid] = item
            size += needed
        else:
            if eid in pinned:
                raise ValueError("Pinned evidence exceeds the saved run allowance.")
            rejection = RejectedEvidence(
                id=stable_id("rejection", eid, "retention", state["iteration_count"]),
                candidate_id=eid,
                source_id=parsed[eid].source_id,
                reason="evidence_limit",
                rationale=(
                    "Lower relevance passage omitted from the active store; "
                    "original source snapshot and acquisition retained."
                ),
            )
            rejected[rejection.id] = state["rejected_evidence"].get(rejection.id) or record_data(
                rejection
            )
    removed = set(state["evidence_store"]) - set(selected)
    update: dict[str, object] = {
        "evidence_store": Overwrite(selected),
        "rejected_evidence": rejected,
    }
    if removed:
        update.update(
            coverage_by_question={},
            coverage_status="missing",
            coverage_signature=None,
            last_coverage_pass=None,
            propositions={},
            comparisons={},
            analysis_signature=None,
            last_analysis_pass=None,
        )
    return update
