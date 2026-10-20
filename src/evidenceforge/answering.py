"""Short exact excerpts for report presentation; no new claims or model calls."""

import html
import re
from dataclasses import dataclass, replace

from evidenceforge.graph.state import StateSnapshot
from evidenceforge.nodes.extraction import readable_spans
from evidenceforge.presentation import TABLE, adjacent_role, display_issues, future_years

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
HOW_TO = re.compile(
    r"^\s*how\s+(?:(?:can|do|should|would|could)\s+(?:i|we|you|one)\s+)?"
    r"(?:to\s+)?(?:become|start|build|create|learn|establish|launch|develop|set\s+up)\b",
    re.I,
)
PLAN_GENERIC = frozenset(
    "essential steps typical phases common identify list describe requirements including "
    "establishing focused least three first second third can i we you my your should would".split()
)
PROMOTIONAL = re.compile(
    r"\b(?:subscribe|like and share|my course|my school|my community|our course|"
    r"join my|join our|profile picture|follow original audio)\b|\[music\]",
    re.I,
)


@dataclass(frozen=True)
class AnswerExcerpt:
    claim_id: str
    evidence_id: str
    start_offset: int
    end_offset: int
    text: str
    criterion: str | None = None


def words(text: str) -> set[str]:
    return set(re.findall(r"[^\W\d_]+|\d+(?:\.\d+)?", text.casefold())) - QUESTION_WORDS


CRITERION_GENERIC = frozenset(
    "identify identifies list lists name names specify specifies core essential key typical "
    "typically necessary relevant development foundational foundations fields field study "
    "role roles industry standards requirements required skills learning paths recognized "
    "reputable professional practical specific used".split()
)


def criterion_words(text: str) -> set[str]:
    equivalents = {
        "educational": "education",
        "academic": "education",
        "mathematical": "mathematics",
        "statistical": "statistics",
    }
    return {
        word[:-1] if word.endswith("s") and len(word) > 4 else word
        for term in words(text) - PLAN_GENERIC - CRITERION_GENERIC
        for word in (equivalents.get(term, term),)
    }


def criterion_topic_matches(criterion: str, passage: str) -> bool:
    topics = (
        r"portfolio|projects?",
        r"linear algebra|mathematic\w*|statistic\w*|probability|calculus",
        r"frameworks?|pytorch|tensorflow|scikit.learn",
        r"degrees?|education|academic",
    )
    for topic in topics:
        if re.search(topic, criterion, re.I):
            return bool(re.search(topic, passage, re.I))
    return True


def unresolved_answer(snapshot: StateSnapshot) -> bool:
    report = snapshot.final_report
    if report is None:
        return False
    anchors = words(snapshot.request.question)
    procedural = bool(HOW_TO.search(snapshot.request.question))
    plan_topics = set().union(
        *(words(question.question) - PLAN_GENERIC for question in snapshot.research_questions)
    )

    coverage_texts = {
        snapshot.evidence_store[eid].passage
        for coverage in snapshot.coverage_by_question.values()
        for eid in coverage.evidence_ids
    }

    def relevant(text: str) -> bool:
        terms = words(text)
        if procedural:
            return text in coverage_texts or len(terms & (anchors | plan_topics)) >= 2
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
    procedural = bool(HOW_TO.search(snapshot.request.question))
    planned = {
        q.id: words(q.question + " " + " ".join(q.acceptance_criteria)) - PLAN_GENERIC
        for q in snapshot.research_questions
    }
    answer_claims = {
        cid
        for section in report.sections
        if section.name in {"summary", "key_findings"}
        for cid in section.claim_ids
    }
    for cid in cited:
        if cid not in accepted or cid not in answer_claims:
            continue
        claim = snapshot.report_claims[cid]
        for eid in claim.evidence_ids:
            evidence = snapshot.evidence_store[eid]
            if claim.statement != evidence.passage:
                continue
            text = evidence.passage
            if future_years(
                text, snapshot.started_at.year, snapshot.request.question
            ) or adjacent_role(text, snapshot.request.question):
                continue
            spans = [(0, len(text))] if QUALIFIER.search(text) else list(readable_spans(text, 1))
            # A longer whole passage can preserve a how-to answer and all its caveats.
            # It is a fallback, never permission to shorten away qualifications.
            if procedural and (0, len(text)) not in spans:
                spans.append((0, len(text)))
            for start, end in spans:
                excerpt = text[start:end]
                decoded = html.unescape(excerpt)
                context_fallback = procedural and start == 0 and end == len(text)
                if (
                    not 8
                    <= len(excerpt)
                    <= (1600 if context_fallback else 650 if procedural else 320)
                    or NOISE.search(decoded)
                    or PROMOTIONAL.search(decoded)
                    or TABLE.search(decoded)
                    or display_issues(
                        decoded, year=snapshot.started_at.year, request=snapshot.request.question
                    )
                    or DEPENDENT_START.search(excerpt.lstrip())
                    or (start > 0 and CONTEXT.search(text[:start]))
                ):
                    continue
                overlap = words(excerpt) & anchors
                plan_anchors = set().union(*(planned.get(qid, set()) for qid in claim.question_ids))
                plan_overlap = words(decoded) & plan_anchors
                if procedural:
                    assessed = any(
                        eid in snapshot.coverage_by_question[qid].evidence_ids
                        for qid in claim.question_ids
                        if qid in snapshot.coverage_by_question
                    )
                    if len(overlap | plan_overlap) < 2 and not (assessed and context_fallback):
                        continue
                elif not overlap or len(overlap) / len(anchors) < 0.5:
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
                if procedural:
                    # Repeating the user's topic is weaker than giving concrete guidance.
                    score *= 0.25
                    score += min(0.5, len(plan_overlap) / max(1, len(plan_anchors)))
                if procedural:
                    # Favor concrete content over short sentences repeating the job/topic.
                    detail = (
                        words(decoded)
                        - anchors
                        - PLAN_GENERIC
                        - {
                            "become",
                            "engineer",
                            "engineering",
                            "ai",
                            "successful",
                            "good",
                            "strong",
                            "foundation",
                            "foundational",
                            "step",
                            "needs",
                            "need",
                        }
                    )
                    score += min(0.3, len(detail) / 70)
                    if re.search(
                        r"\b(?:build|learn|test|deploy|validate|practice|implement|"
                        r"programming|python|mathematics|statistics|portfolio|projects|"
                        r"monitoring|interviews|evaluate|testing)\b",
                        decoded,
                        re.I,
                    ):
                        score += 0.4
                    concrete = re.findall(
                        r"\b(?:python|java|sql|numpy|pandas|pytorch|scikit-learn|"
                        r"linear algebra|probability|statistics|calculus|portfolio|"
                        r"projects|deploy(?:ment)?|monitoring|interviews|"
                        r"validate|testing|measured|prototype)\b",
                        decoded,
                        re.I,
                    )
                    score += min(0.8, len(set(word.casefold() for word in concrete)) * 0.2)
                if len(excerpt) > 320:
                    score -= 0.5
                if re.search(r"\b(?:is|are|means|refers to)\b", excerpt, re.I):
                    score += 0.1
                candidates.append(
                    (
                        score,
                        len(excerpt),
                        AnswerExcerpt(cid, eid, start, end, excerpt),
                        overlap | plan_overlap if procedural else overlap,
                    )
                )
    selected: list[AnswerExcerpt] = []
    covered: set[str] = set()
    seen: set[str] = set()
    ranked = sorted(candidates, key=lambda item: (-item[0], item[1]))

    def redundant(excerpt: AnswerExcerpt) -> bool:
        return any(
            excerpt.text in previous.text
            or previous.text in excerpt.text
            or len(words(excerpt.text) & words(previous.text))
            / max(1, len(words(excerpt.text) | words(previous.text)))
            > 0.65
            for previous in selected
        )

    if procedural:
        # Cover distinct approved criteria before adding more detail on one topic.
        # These labels organize exact quotations; they do not assert new facts.
        for question in snapshot.research_questions:
            for criterion in question.acceptance_criteria:
                terms = criterion_words(criterion) - criterion_words(snapshot.request.question)
                matches = [
                    (
                        len(criterion_words(item[2].text) & terms) / max(1, len(terms)),
                        item,
                    )
                    for item in ranked
                    if question.id in snapshot.report_claims[item[2].claim_id].question_ids
                    and len(criterion_words(item[2].text) & terms) >= min(2, len(terms))
                    and terms
                    and criterion_topic_matches(criterion, item[2].text)
                    and not redundant(item[2])
                ]
                if matches and len(selected) < 5:
                    _, chosen = max(matches, key=lambda pair: (pair[0], pair[1][0]))
                    criterion_excerpt = replace(chosen[2], criterion=criterion)
                    selected.append(criterion_excerpt)
                    seen.add(criterion_excerpt.text)
                    covered.update(chosen[3])
    for _, _, selected_excerpt, overlap in ranked:
        if len(selected) >= (5 if procedural else 3):
            break
        if selected_excerpt.text in seen or (not procedural and not overlap - covered):
            continue
        if procedural and redundant(selected_excerpt):
            continue
        selected.append(selected_excerpt)
        seen.add(selected_excerpt.text)
        covered.update(overlap)
        if not procedural and anchors.issubset(covered):
            break
    return tuple(selected)


def criterion_label(criterion: str) -> str:
    """Readable navigation labels derived from an approved criterion, not new claims."""
    for pattern, label in (
        (r"education|degrees?|certifications?|academic", "Education and training"),
        (r"programming|languages?|frameworks?|tools?", "Programming and tools"),
        (
            r"machine learning|deep learning|mathematical|mathematics|"
            r"statistical|statistics|technical skills",
            "Technical foundations",
        ),
        (r"portfolio|projects?|practical|open.source", "Practical experience"),
        (r"career|entry points?|transition", "Career steps"),
    ):
        if re.search(pattern, criterion, re.I):
            return label
    return criterion
