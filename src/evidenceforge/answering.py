"""Short exact excerpts for report presentation; no new claims or model calls."""

import re
from dataclasses import dataclass

from evidenceforge.graph.state import StateSnapshot
from evidenceforge.nodes.extraction import readable_spans

QUESTION_WORDS = frozenset(
    "what which who whose where when why how is are was were do does did a an the "
    "of in on at to for from with and or me please tell give explain describe "
    "compare comparison between about state city country current currently".split()
)
NOISE = re.compile(
    r"may be an image|follow original audio|profile picture|log in|sign in|"
    r"cookie|click here|read more|frequently asked questions|https?://|www\.|"
    r"<[^>]+>|&(?:#\w+|\w+);|\?",
    re.I,
)
QUALIFIER = re.compile(
    r"\b(?:not|never|no longer|formerly|until|if|unless|however|but|except|"
    r"excludes?|excluding|only|may|might|could|disputed|incorrect|outdated|"
    r"false|untrue|wrong|misleading|inaccurate|unverified|uncertain)\b",
    re.I,
)
CONTEXT = re.compile(r"\b(?:\d{4}|historically|previously|as of|following|after|before)\b", re.I)
DEPENDENT_START = re.compile(r"^(?:it|this|that|these|those|they|he|she|there)\b", re.I)


@dataclass(frozen=True)
class AnswerExcerpt:
    claim_id: str
    evidence_id: str
    start_offset: int
    end_offset: int
    text: str


def words(text: str) -> set[str]:
    return set(re.findall(r"[^\W\d_]+|\d+(?:\.\d+)?", text.casefold())) - QUESTION_WORDS


def unresolved_answer(snapshot: StateSnapshot) -> bool:
    report = snapshot.final_report
    if report is None:
        return False
    anchors = words(snapshot.request.question)

    def relevant(text: str) -> bool:
        terms = words(text)
        return bool(anchors) and (
            anchors.issubset(terms)
            if "capital" in anchors
            else len(terms & anchors) / len(anchors) >= 0.5
        )

    cited_evidence = {
        eid
        for section in report.sections
        for cid in section.claim_ids
        for eid in snapshot.report_claims[cid].evidence_ids
    }
    return any(
        item.relationship in {"contradicts", "not_comparable"}
        and any(
            snapshot.propositions[pid].evidence_id in cited_evidence
            and relevant(snapshot.propositions[pid].quote)
            for pid in (item.left_id, item.right_id)
        )
        for item in snapshot.comparisons.values()
    ) or any(
        section.name == "disagreements"
        and any(relevant(snapshot.report_claims[cid].statement) for cid in section.claim_ids)
        for section in report.sections
    )


def answer_excerpts(snapshot: StateSnapshot) -> tuple[AnswerExcerpt, ...]:
    """Rank bounded, exact cited spans; never choose a winner for a dispute.

    This is lexical presentation, not a new semantic or source-truth assessment.
    Qualifiers stay with their whole quotation, or no short excerpt is offered.
    """
    report = snapshot.final_report
    if report is None or unresolved_answer(snapshot):
        return ()
    anchors = words(snapshot.request.question)
    if not anchors:
        return ()
    accepted = {
        audit.claim_id
        for audit in snapshot.citation_audit
        if audit.structural_valid and audit.support == "supported"
    }
    cited = dict.fromkeys(cid for section in report.sections for cid in section.claim_ids)
    candidates: list[tuple[float, int, AnswerExcerpt, set[str]]] = []
    for cid in cited:
        if cid not in accepted:
            continue
        claim = snapshot.report_claims[cid]
        for eid in claim.evidence_ids:
            evidence = snapshot.evidence_store[eid]
            if claim.statement != evidence.passage:
                continue
            text = evidence.passage
            spans = [(0, len(text))] if QUALIFIER.search(text) else list(readable_spans(text, 1))
            for start, end in spans:
                excerpt = text[start:end]
                if (
                    not 8 <= len(excerpt) <= 320
                    or NOISE.search(excerpt)
                    or DEPENDENT_START.search(excerpt.lstrip())
                    or (start > 0 and CONTEXT.search(text[:start]))
                ):
                    continue
                overlap = words(excerpt) & anchors
                if not overlap or len(overlap) / len(anchors) < 0.5:
                    continue
                if "capital" in anchors and (
                    not anchors.issubset(words(excerpt))
                    or not re.search(
                        r"\b(?:is|are)\b[^.!?]{0,80}\bcapital\b"
                        r"|\bcapital\b[^.!?]{0,80}\b(?:is|are)\b",
                        excerpt,
                        re.I,
                    )
                ):
                    continue
                score = len(overlap) / len(anchors)
                if re.search(r"\b(?:is|are|means|refers to)\b", excerpt, re.I):
                    score += 0.1
                candidates.append(
                    (score, len(excerpt), AnswerExcerpt(cid, eid, start, end, excerpt), overlap)
                )
    selected: list[AnswerExcerpt] = []
    covered: set[str] = set()
    seen: set[str] = set()
    for _, _, selected_excerpt, overlap in sorted(candidates, key=lambda item: (-item[0], item[1])):
        if selected_excerpt.text in seen or not overlap - covered:
            continue
        selected.append(selected_excerpt)
        seen.add(selected_excerpt.text)
        covered.update(overlap)
        if anchors.issubset(covered) or len(selected) == 3:
            break
    return tuple(selected)
