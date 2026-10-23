"""Short exact excerpts for report presentation; no new claims or model calls."""

import html
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, replace

from evidenceforge.evidence.coverage_detail import enumerative_support
from evidenceforge.graph.state import StateSnapshot
from evidenceforge.presentation import (
    SCOPE,
    TABLE,
    adjacent_role,
    display_issues,
    editorial_biography,
    future_years,
    presentation_spans,
)

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
CONTEXT = re.compile(r"\b(?:\d{4}|historically|previously|as of|following|after|before)\b", re.I)
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
    display_label: str | None = None


def matching_text(text: str) -> str:
    """Normalize typography only for matching, never source text or offsets."""
    return unicodedata.normalize("NFKC", html.unescape(text))


def words(text: str) -> set[str]:
    return (
        set(re.findall(r"[^\W\d_]+|\d+(?:\.\d+)?", matching_text(text).casefold())) - QUESTION_WORDS
    )


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
    criterion, passage = matching_text(criterion), matching_text(passage)
    if (
        re.search(r"\blanguages?\b", criterion, re.I)
        and re.search(r"\b(?:frameworks?|libraries)\b", criterion, re.I)
        and re.search(r"\band\b", criterion, re.I)
        and not re.search(r"\b(?:programming|coding|languages?)\b", passage, re.I)
    ):
        return False
    topics = (
        r"linear algebra|mathematic\w*|statistic\w*|probability|calculus",
        r"frameworks?|pytorch|tensorflow|scikit.learn",
        r"degrees?|education|academic",
    )
    return (
        all(
            re.search(topic, passage, re.I) for topic in topics if re.search(topic, criterion, re.I)
        )
        and (
            not re.search(r"portfolio|projects?", criterion, re.I)
            or bool(
                re.search(r"portfolio|projects?", passage, re.I) or PROJECT_EXAMPLES.search(passage)
            )
        )
        and (not career_criterion(criterion) or bool(CAREER_EVIDENCE.search(passage)))
    )


CAREER_EVIDENCE = re.compile(
    r"\b(?:entry[- ]level|entry points?|junior|intern(?:ships?)?|apprenticeships?|job titles?|"
    r"apply for|transitions?|progress(?:es|ion)? from)\b",
    re.I,
)
PROJECT_EXAMPLES = re.compile(
    r"\bprojects?\s*[:(]|\b(?:practical\s+)?exercises?\s+(?:like|including)\b|"
    r"\b(?:for example|such as|e\.g\.)\b",
    re.I,
)


def career_criterion(criterion: str) -> bool:
    return bool(
        re.search(
            r"entry[- ]level|entry points?|career|professional (?:roles|progression|pathways)|"
            r"role transitions?",
            criterion,
            re.I,
        )
    )


def criterion_fit(criterion: str, passage: str, request: str) -> float | None:
    criterion, passage = matching_text(criterion), matching_text(passage)
    terms = criterion_words(criterion) - criterion_words(request)
    overlap = len(criterion_words(passage) & terms)
    career = career_criterion(criterion) and bool(CAREER_EVIDENCE.search(passage))
    examples = bool(
        re.search(r"portfolio|projects?", criterion, re.I) and PROJECT_EXAMPLES.search(passage)
    )
    framework_list = bool(
        re.search(r"frameworks?|libraries", criterion, re.I)
        and re.search(r"\b(?:frameworks?|libraries)\s*:", passage, re.I)
    )
    if (
        not terms
        or not criterion_topic_matches(criterion, passage)
        or not enumerative_support(criterion, (passage,))
    ):
        return None
    foundation_list = bool(
        overlap and re.search(r"mathematic\w*|statistic\w*|foundations?", criterion, re.I)
    )
    if overlap < min(2, len(terms)) and not (
        career or examples or framework_list or foundation_list
    ):
        return None
    return overlap / len(terms) + (
        1.5 if examples else 1.0 if career else 0.75 if framework_list else 0.0
    )


_BULLET_HEADING = re.compile(
    r"(?m)^[ \t]*[\u2022\u25cf\u25aa\u25e6\U0001f539][ \t]+[^\n.!?]{1,80}\n"
)
_LANGUAGE_NAMES = re.compile(r"\b(?:python|sql|java(?:script)?|typescript|c\+\+|c#)(?!\w)", re.I)
_FRAMEWORK_NAMES = re.compile(
    r"\b(?:pytorch|tensorflow|scikit[- ]learn|keras|langchain|llamaindex)\b", re.I
)


def bullet_heading_spans(text: str) -> Iterator[tuple[int, int]]:
    """Keep an exact independent bullet heading with its complete body.

    A caveat anywhere in the original passage may govern subsequent items, so
    do not split that passage. Unheaded introductory fragments are not blocks.
    """
    if SCOPE.search(text):
        return
    markers = list(_BULLET_HEADING.finditer(text))
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        start = (
            marker.start()
            + len(text[marker.start() : end])
            - len(text[marker.start() : end].lstrip())
        )
        end = start + len(text[start:end].rstrip())
        if text[marker.end() : end].strip():
            yield start, end


def compound_tools_criterion(criterion: str) -> bool:
    """Recognize an unnumbered language-and-framework inventory, not arbitrary AND."""
    text = matching_text(criterion)
    return bool(
        re.search(r"\b(?:programming\s+)?languages?\b", text, re.I)
        and re.search(r"\b(?:frameworks?|libraries)\b", text, re.I)
        and re.search(r"\band\b", text, re.I)
        and not re.search(r"\b(?:[1-9]\d*|one|two|three|four|five|six)\b", text, re.I)
    )


def tool_facet_fit(passage: str, facet: str) -> float | None:
    """Locate concrete named content for one displayed part of a compound criterion.

    This organizes already audited quotations; it is not a new semantic audit.
    Named tools alone are insufficient without category or headed-item context.
    """
    text = matching_text(passage)
    if facet == "languages":
        names = _LANGUAGE_NAMES.findall(text)
        explicit = bool(re.search(r"\b(?:programming|coding|languages?)\b", text, re.I))
        context = bool(
            re.search(
                r"\b(?:learn|master|required|primary|used|uses|essential|programming|coding)\b",
                text,
                re.I,
            )
        )
    else:
        names = _FRAMEWORK_NAMES.findall(text)
        explicit = bool(re.search(r"\b(?:frameworks?|libraries)\b", text, re.I))
        first_line, separator, body = text.partition("\n")
        heading = bool(
            separator
            and _FRAMEWORK_NAMES.search(first_line)
            and re.fullmatch(
                r"\s*[\u2022\u25cf\u25aa\u25e6\U0001f539]\s+"
                r"(?:pytorch|tensorflow|scikit[- ]learn|keras|langchain|llamaindex)\s*",
                first_line,
                re.I,
            )
        )
        explicit = explicit or bool(
            heading
            and re.search(
                r"\b(?:learning|research|models?|prototyp\w*|deployment|systems?|"
                r"graphs?|data|training|ML)\b",
                body,
                re.I,
            )
        )
        context = explicit
    if not names or not explicit or not context:
        return None
    return 1.0 + min(0.75, len({name.casefold() for name in names}) * 0.25)


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
            if (
                future_years(text, snapshot.started_at.year, snapshot.request.question)
                or adjacent_role(text, snapshot.request.question)
                or editorial_biography(text, snapshot.request.question)
            ):
                continue
            spans = list(presentation_spans(text))
            if procedural:
                spans.extend(span for span in bullet_heading_spans(text) if span not in spans)
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
                    focused = assessed and any(
                        criterion_fit(criterion, decoded, snapshot.request.question) is not None
                        or (
                            compound_tools_criterion(criterion)
                            and any(
                                tool_facet_fit(decoded, facet) is not None
                                for facet in ("languages", "frameworks")
                            )
                        )
                        for q in snapshot.research_questions
                        if q.id in claim.question_ids
                        for criterion in q.acceptance_criteria
                    )
                    if len(overlap | plan_overlap) < 2 and not (
                        assessed and (context_fallback or focused)
                    ):
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
                if compound_tools_criterion(criterion):
                    eligible = [
                        item
                        for item in ranked
                        if question.id in snapshot.report_claims[item[2].claim_id].question_ids
                        and not redundant(item[2])
                    ]
                    pairs = [
                        (left_fit + right_fit + left[0] + right[0], left, right)
                        for left in eligible
                        if (left_fit := tool_facet_fit(left[2].text, "languages")) is not None
                        for right in eligible
                        if (right_fit := tool_facet_fit(right[2].text, "frameworks")) is not None
                        if left[2] == right[2]
                        or not (left[2].text in right[2].text or right[2].text in left[2].text)
                    ]
                    if pairs:
                        _, left, right = max(pairs, key=lambda pair: pair[0])
                        group = (
                            [(left, "Programming and tools")]
                            if left[2] == right[2]
                            else [
                                (left, "Programming languages"),
                                (right, "Frameworks and libraries"),
                            ]
                        )
                        # Both components must have audited content and display room.
                        if len(selected) + len(group) <= 6:
                            for chosen, label in group:
                                excerpt = replace(
                                    chosen[2], criterion=criterion, display_label=label
                                )
                                selected.append(excerpt)
                                seen.add(excerpt.text)
                                covered.update(chosen[3])
                            continue
                matches = [
                    (fit, item)
                    for item in ranked
                    if question.id in snapshot.report_claims[item[2].claim_id].question_ids
                    and not redundant(item[2])
                    and (fit := criterion_fit(criterion, item[2].text, snapshot.request.question))
                    is not None
                ]
                if matches and len(selected) < 6:
                    _, chosen = max(matches, key=lambda pair: (pair[0], pair[1][0]))
                    criterion_excerpt = replace(chosen[2], criterion=criterion)
                    selected.append(criterion_excerpt)
                    seen.add(criterion_excerpt.text)
                    covered.update(chosen[3])
        if selected:
            return tuple(selected)
    for _, _, selected_excerpt, overlap in ranked:
        if len(selected) >= (6 if procedural else 3):
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
    if career_criterion(criterion):
        return "Career steps"
    programming = bool(re.search(r"programming|languages?", criterion, re.I))
    frameworks = bool(re.search(r"frameworks?|libraries", criterion, re.I))
    if programming and not frameworks:
        return "Programming languages"
    if frameworks and not programming:
        return "Frameworks and libraries"
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
