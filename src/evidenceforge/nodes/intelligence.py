"""Replace analysis projections after each retained evidence batch."""

from typing import cast

from pydantic import JsonValue

from evidenceforge.evidence.contracts import AnalysisOptions
from evidenceforge.evidence.propositions import UNITS, compare_all, extract
from evidenceforge.evidence.ranking import rank
from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.identity import stable_id
from evidenceforge.nodes.common import Update, checked_patch, record_data
from evidenceforge.nodes.quality_common import quality_event


class EvidenceIntelligence:
    def __init__(self, options: AnalysisOptions) -> None:
        self.options = options

    def __call__(self, state: ResearchState) -> Update:
        s = StateSnapshot.model_validate(state)
        if s.run_status != "running":
            return {}
        extracted = tuple(
            p for eid in sorted(s.evidence_store) for p in extract(s.evidence_store[eid])
        )
        selected = extracted[: self.options.max_propositions]
        comparisons, pair_limited = compare_all(selected, self.options.max_comparisons)
        propositions = {p.id: p for p in selected}
        rankings = rank(
            s.source_records,
            s.evidence_store,
            propositions,
            comparisons,
            self.options.ranking_profile,
            s.started_at.date(),
        )
        parsed = {p.evidence_id for p in selected}
        notes = [
            f"{len(parsed)} of {len(s.evidence_store)} passages matched numeric scope grammar; "
            "other passages remain unclassified."
        ]
        limited = len(selected) < len(extracted) or pair_limited
        if limited:
            notes.append("Analysis cap reached; comparison coverage is incomplete.")
        return checked_patch(
            state,
            {
                "coverage_status": "missing",
                "source_quality": {sid: record_data(q) for sid, q in rankings.items()},
                "propositions": {pid: record_data(p) for pid, p in propositions.items()},
                "comparisons": {c.id: record_data(c) for c in comparisons},
                "analysis_signature": stable_id(
                    "analysis",
                    cast(
                        JsonValue,
                        sorted(
                            {
                                stable_id(
                                    "measurement",
                                    p.entity,
                                    p.metric,
                                    p.timeframe,
                                    p.population,
                                    p.conditions,
                                    UNITS[p.unit][0],
                                    str((p.value * UNITS[p.unit][1]).normalize()),
                                )
                                for p in selected
                            }
                        ),
                    ),
                ),
                "last_analysis_pass": s.iteration_count,
                "analysis_notes": notes,
                "analysis_limited": limited,
                **quality_event(
                    state,
                    "evidence_intelligence",
                    "Ranked metadata and compared explicit scoped numeric propositions.",
                ),
            },
        )
