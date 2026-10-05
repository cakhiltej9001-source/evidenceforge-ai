"""Deduplicate literal working passages without rewriting retained provenance."""

from collections.abc import Iterable, Mapping

from evidenceforge.schemas import Contract, Count, EvidenceItem, EvidenceLocator, Identifier


class DuplicateEvidence(Contract):
    representative_id: Identifier
    evidence_id: Identifier
    source_id: Identifier
    acquisition_ids: tuple[Identifier, ...]
    question_ids: tuple[Identifier, ...]
    locator: EvidenceLocator
    representative_start: Count
    representative_end: Count


class WorkingEvidence(Contract):
    evidence: tuple[EvidenceItem, ...]
    duplicates: tuple[DuplicateEvidence, ...]


def working_evidence(
    evidence: Iterable[EvidenceItem], scores: Mapping[str, float] | None = None
) -> WorkingEvidence:
    """Keep a full exact span covering each omitted span and all its question links.

    Original records remain immutable in the evidence ledger. Different wording,
    qualifiers, owners and unrepresented question associations are never collapsed.
    Equality/containment is textual redundancy, not independent corroboration.
    """
    scores = scores or {}
    selected: list[EvidenceItem] = []
    duplicates: list[DuplicateEvidence] = []
    ordered = sorted(
        evidence,
        key=lambda e: (
            -len(e.question_ids),
            -len(e.passage),
            -scores.get(e.source_id, 0.5),
            e.id,
        ),
    )
    for item in ordered:
        representative = next(
            (
                candidate
                for candidate in selected
                if candidate.owner_scope == item.owner_scope
                and set(item.question_ids).issubset(candidate.question_ids)
                and item.passage in candidate.passage
            ),
            None,
        )
        if representative is None:
            selected.append(item)
            continue
        start = representative.passage.index(item.passage)
        duplicates.append(
            DuplicateEvidence(
                representative_id=representative.id,
                evidence_id=item.id,
                source_id=item.source_id,
                acquisition_ids=item.acquisition_ids,
                question_ids=item.question_ids,
                locator=item.locator,
                representative_start=start,
                representative_end=start + len(item.passage),
            )
        )
    # Preserve the established ranking order after choosing the spanning representatives.
    selected.sort(key=lambda e: (-scores.get(e.source_id, 0.5), e.id))
    return WorkingEvidence(evidence=tuple(selected), duplicates=tuple(duplicates))
