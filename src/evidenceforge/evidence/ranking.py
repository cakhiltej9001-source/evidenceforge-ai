"""Transparent weighted metadata heuristics; scores are not truth probabilities."""

from datetime import date

from evidenceforge.evidence.contracts import (
    Comparison,
    Proposition,
    RankingFeature,
    RankingProfile,
    SourceQuality,
)
from evidenceforge.identity import stable_id
from evidenceforge.schemas import EvidenceItem, SourceRecord

PROFILES = {
    "general": (0.35, 0.25, 0.10, 0.10, 0.05, 0.10, 0.05),
    "current": (0.30, 0.25, 0.08, 0.10, 0.12, 0.10, 0.05),
    "historical": (0.40, 0.25, 0.10, 0.10, 0.00, 0.10, 0.05),
}


def families(sources: dict[str, SourceRecord]) -> dict[str, str]:
    parent = {sid: sid for sid in sources}

    def find(sid: str) -> str:
        while parent[sid] != sid:
            sid = parent[sid]
        return sid

    by_family: dict[str, str] = {}
    by_hash: dict[str, str] = {}
    for sid in sorted(sources):
        source = sources[sid]
        for registry, key in ((by_family, source.source_family), (by_hash, source.content_hash)):
            if key is None:
                continue
            if key in registry:
                a, b = sorted((find(sid), find(registry[key])))
                parent[b] = a
            else:
                registry[key] = sid
    group_hashes: dict[str, list[str]] = {}
    for sid, source in sources.items():
        group_hashes.setdefault(find(sid), []).append(source.content_hash)
    return {sid: stable_id("family_group", min(group_hashes[find(sid)])) for sid in sources}


def rank(
    sources: dict[str, SourceRecord],
    evidence: dict[str, EvidenceItem],
    propositions: dict[str, Proposition],
    comparisons: tuple[Comparison, ...],
    profile: RankingProfile,
    as_of: date,
) -> dict[str, SourceQuality]:
    groups = families(sources)
    corroboration: dict[str, set[str]] = {sid: set() for sid in sources}
    measured: set[str] = set()
    for p in propositions.values():
        measured.add(evidence[p.evidence_id].source_id)
    for c in comparisons:
        a = evidence[propositions[c.left_id].evidence_id].source_id
        b = evidence[propositions[c.right_id].evidence_id].source_id
        if c.relationship == "supports" and groups[a] != groups[b]:
            # Family metadata is required; distinct unknown records are not independent votes.
            if sources[a].source_family and sources[b].source_family:
                corroboration[a].add(groups[b])
                corroboration[b].add(groups[a])
    weights = PROFILES[profile]
    results = {}
    for sid in sorted(sources):
        s = sources[sid]
        matches = [e.relevance for e in evidence.values() if e.source_id == sid]
        recency = None
        if s.publication_date:
            try:
                age = (as_of - date.fromisoformat(s.publication_date)).days
                if age >= 0:
                    recency = max(0.0, 1.0 - age / 3650)
            except ValueError:
                pass
        size = sum(group == groups[sid] for group in groups.values())
        values = (
            (
                "relevance",
                max(matches) if matches else None,
                "Maximum admitted lexical relevance; not semantic verification.",
            ),
            (
                "primary_evidence",
                None if s.primary_evidence is None else float(s.primary_evidence),
                s.metadata_rationale or "Primary-evidence metadata is unknown.",
            ),
            (
                "publisher_identity",
                1.0 if s.publisher else None,
                "A supplied publisher name is an identity signal, not verified authority.",
            ),
            (
                "methodology",
                None if s.methodology_transparent is None else float(s.methodology_transparent),
                s.metadata_rationale or "Methodological transparency is unknown.",
            ),
            (
                "recency",
                recency,
                "ISO publication date uses a ten-year decay from run start; "
                "absent, invalid or future dates are unknown.",
            ),
            (
                "independent_corroboration",
                min(1.0, len(corroboration[sid]) / 2)
                if sid in measured and s.source_family
                else None,
                "Equal measurements across known families; copied text is excluded. "
                "Family labels are supplied signals.",
            ),
            (
                "family_uniqueness",
                1.0 / size,
                "Same supplied family or content hash is grouped; copies add no votes.",
            ),
        )
        features = tuple(
            RankingFeature(name=name, value=value, weight=weight, rationale=reason)
            for (name, value, reason), weight in zip(values, weights, strict=True)
        )
        results[sid] = SourceQuality(
            source_id=sid,
            profile=profile,
            score=sum(f.weight * (0.5 if f.value is None else f.value) for f in features),
            observed_weight=sum(f.weight for f in features if f.value is not None),
            family_group=groups[sid],
            family_size=size,
            features=features,
        )
    return results
