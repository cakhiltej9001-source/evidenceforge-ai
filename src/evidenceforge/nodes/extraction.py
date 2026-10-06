"""Extract exact retained spans; lexical relevance is an admission heuristic, not truth."""

import re
from collections.abc import Iterator

from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.identity import stable_id
from evidenceforge.nodes.common import Update, checked_patch, record_data
from evidenceforge.retrieval.contracts import ArtifactFailure, RetrievalOptions
from evidenceforge.schemas import EvidenceItem, EvidenceLocator, RejectedEvidence, RunEvent
from evidenceforge.storage.artifacts import ArtifactStore

STOP_WORDS = frozenset(
    "a an the and or is are be to of in on for with what which how does do "
    "primary evidence definitions set scope limitations affect conclusions about "
    "synthetic fixture sources relevant passage".split()
)


def tokens(text: str) -> set[str]:
    return {word for word in re.findall(r"\w+", text.casefold()) if word not in STOP_WORDS}


def spans(text: str, size: int) -> Iterator[tuple[int, int]]:
    """Character offsets into the stored text; preserve every returned character."""
    start = 0
    for boundary in [m.start() for m in re.finditer(r"\n\s*\n", text)] + [len(text)]:
        for offset in range(start, boundary, size):
            end = min(boundary, offset + size)
            if text[offset:end].strip():
                yield offset, end
        if boundary < len(text):
            separator = re.match(r"\n\s*\n", text[boundary:])
            start = boundary + (separator.end() if separator else 0)


class EvidenceExtractor:
    def __init__(
        self, artifacts: ArtifactStore, options: RetrievalOptions, *, evict_lowest: bool = False
    ) -> None:
        self.artifacts, self.options = artifacts, options
        self.evict_lowest = evict_lowest

    def __call__(self, state: ResearchState) -> Update:
        snapshot = StateSnapshot.model_validate(state)
        if snapshot.run_status != "running" or snapshot.iteration_count == 0:
            return {}
        groups: dict[tuple[str, str], list[str]] = {}
        for acquisition in snapshot.source_acquisitions.values():
            if (
                snapshot.query_records[acquisition.query_id].research_pass
                == snapshot.iteration_count
            ):
                groups.setdefault((acquisition.source_id, acquisition.snapshot_id), []).append(
                    acquisition.id
                )
        evidence, rejected = {}, {}
        total_count = len(snapshot.evidence_store)
        total_bytes = sum(len(e.passage.encode("utf-8")) for e in snapshot.evidence_store.values())

        def reject(candidate: str, source: str, reason: str, rationale: str) -> None:
            item = RejectedEvidence(
                id=stable_id("rejection", candidate, reason),
                candidate_id=candidate,
                source_id=source,
                reason=reason,
                rationale=rationale,
            )
            rejected[item.id] = state["rejected_evidence"].get(item.id) or record_data(item)

        for (source_id, snapshot_id), acquisition_ids in sorted(groups.items()):
            candidate = stable_id("candidate", snapshot.owner_scope, source_id, snapshot_id)
            try:
                content = self.artifacts.read(snapshot.raw_result_refs[snapshot_id])
            except ArtifactFailure:
                reject(
                    candidate,
                    source_id,
                    "parse_failed",
                    "Retained source failed its integrity check.",
                )
                continue
            questions = {
                qid
                for aid in acquisition_ids
                for qid in snapshot.query_records[
                    snapshot.source_acquisitions[aid].query_id
                ].question_ids
            }
            acquired = snapshot.source_acquisitions[acquisition_ids[0]]
            produced = 0
            for start, end in spans(content, self.options.passage_chars):
                passage = content[start:end]
                identifier = stable_id(
                    "evidence", snapshot.owner_scope, source_id, snapshot_id, start, end
                )
                if produced >= self.options.max_passages_per_source:
                    reject(
                        identifier, source_id, "evidence_limit", "Per-source passage limit reached."
                    )
                    continue
                passage_tokens = tokens(passage)
                scores = {}
                for question in snapshot.research_questions:
                    if question.id not in questions:
                        continue
                    focus = tokens(question.question)
                    score = len(focus & passage_tokens) / len(focus) if focus else 0.0
                    if score >= self.options.min_relevance and focus & passage_tokens:
                        scores[question.id] = score
                if not scores:
                    reject(
                        identifier,
                        source_id,
                        "irrelevant",
                        "Insufficient lexical overlap with linked questions.",
                    )
                    continue
                old = snapshot.evidence_store.get(identifier)
                if (
                    old is None
                    and not self.evict_lowest
                    and (
                        total_count >= snapshot.budget.max_evidence_count
                        or total_bytes + len(passage.encode("utf-8"))
                        > snapshot.budget.max_evidence_bytes
                    )
                ):
                    reject(
                        identifier,
                        source_id,
                        "evidence_limit",
                        "Run evidence count/byte limit reached.",
                    )
                    continue
                matched = tuple(sorted(scores))
                if old is not None:
                    # Reassess associations; keep the original immutable passage assessment.
                    item = EvidenceItem(
                        **{
                            **old.model_dump(),
                            "acquisition_ids": tuple(
                                sorted(set(old.acquisition_ids) | set(acquisition_ids))
                            ),
                            "question_ids": tuple(sorted(set(old.question_ids) | set(matched))),
                        },
                    )
                    if item == old:
                        produced += 1
                        continue
                else:
                    item = EvidenceItem(
                        id=identifier,
                        source_id=source_id,
                        owner_scope=snapshot.owner_scope,
                        acquisition_ids=tuple(sorted(acquisition_ids)),
                        question_ids=matched,
                        passage=passage,
                        locator=EvidenceLocator(
                            snapshot_id=snapshot_id,
                            start_offset=start,
                            end_offset=end,
                            page=acquired.page,
                            paragraph=acquired.paragraph,
                            section=acquired.section,
                            document_start_offset=acquired.document_start_offset + start
                            if acquired.document_start_offset is not None
                            else None,
                            document_end_offset=acquired.document_start_offset + end
                            if acquired.document_start_offset is not None
                            else None,
                        ),
                        relevance=max(scores.values()),
                        relevance_rationale="Lexical question overlap; not factual verification.",
                    )
                    total_count += 1
                    total_bytes += len(passage.encode("utf-8"))
                if old is not None or len(acquisition_ids) > 1:
                    reject(
                        identifier,
                        source_id,
                        "duplicate",
                        "Duplicate passage retained once; provenance merged.",
                    )
                evidence[item.id] = record_data(item)
                produced += 1
        event = RunEvent(
            id=stable_id("extraction_pass", snapshot.run_id, snapshot.iteration_count),
            kind="evidence_extraction_completed",
            message=(
                f"Admitted or merged {len(evidence)} passages; recorded {len(rejected)} rejections."
            ),
        )
        from evidenceforge.evidence.retention import select_evidence

        retained = (
            select_evidence(state, evidence, rejected)
            if self.evict_lowest
            else {"evidence_store": evidence, "rejected_evidence": rejected}
        )
        return checked_patch(
            state,
            {
                **retained,
                "events": {event.id: state["events"].get(event.id) or record_data(event)},
            },
        )
