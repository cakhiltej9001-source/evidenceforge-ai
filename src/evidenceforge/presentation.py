"""Exact display excerpts, with original evidence and audit records left intact."""

import re
from collections.abc import Iterator

from evidenceforge.evidence.text_quality import aligned_table
from evidenceforge.nodes.extraction import readable_spans

CLUTTER = re.compile(
    r"\b(?:subscribe|like and share|join (?:my|our)|(?:my|our) course|"
    r"placement support|mentor-led program|best .{0,40}courses|"
    r"profile picture|follow original audio|photo by|unsplash|"
    r"frequently asked questions|frequently asked question|read more|click here|"
    r"log in|sign in|cookie policy|privacy policy)\b|"
    r"\[\d{1,2}:\d{2}(?::\d{2})?\]|\[music\]",
    re.I,
)
TABLE = re.compile(r"(?:\|[^|\n]*){3,}|\t[^\n]*\t")
# A qualification elsewhere in the quotation can change a sentence's meaning.
# Keep the entire passage or abstain, rather than silently stripping its caveat.
SCOPE = re.compile(
    r"\b(?:not|never|no|formerly|until|if|unless|however|but|except|"
    r"excludes?|excluding|only|may|might|could|disputed|incorrect|outdated|"
    r"false|untrue|wrong|misleading|inaccurate|unverified|uncertain)\b|\b\w+n['\u2019]t\b",
    re.I,
)
YEARS = re.compile(r"\b(?:19|20|21)\d{2}\b")
TRAINING = re.compile(
    r"\b(?:boot\s?camps?|courses?|programmes?|programs?|certificates?|"
    r"certifications?|credentials?|speciali[sz]ations?)\b",
    re.I,
)
PITCH = re.compile(
    r"\b(?:enrol(?:l)?|sign up|register|apply now|career[- ]ready|job[- ]ready|"
    r"career prep(?:aration)?|placement|mentorship|mentoring|expert mentors?|hands[- ]on|"
    r"is designed to|will help you|our|we offer|acclaimed|world[- ]class|industry readiness|"
    r"boost your resume|solidify your standing)\b|[\w]+['\u2019]s\s+.{0,80}\bboot\s?camp",
    re.I,
)
BRANDED_COURSE = re.compile(
    r"\b[\w&.-]+['\u2019]s\s+[^.!?\n]{0,100}\b(?:courses?|boot\s?camps?|programs?)\b"
    r"[^.!?\n]{0,100}\b(?:cover|provide|offer|help|teach|equip|learners|participants)\w*\b",
    re.I,
)
BIOGRAPHY = re.compile(
    r"\b(?:meet (?:your|the) expert|about (?:the )?author|author bio(?:graphy)?)\b|"
    r"\bin this (?:guide|article),[^.!?]{0,200}\b(?:breaks down|explains|discusses)\b",
    re.I,
)
PAGE_HEADER = re.compile(r"\b(?:updated on|published on|posted on)\b", re.I)
DEPENDENT_START = re.compile(
    r"^(?:it|this|that|these|those|they|he|she|there|yes|because|also|moreover)\b|"
    r"^no(?:\s*[,;:.]|\s+because\b)",
    re.I,
)
QUESTION_TAIL = re.compile(
    r"\b(?:What|Which|Where|When|Why|How|Is|Are|Do|Does|Can|Should)\b[^.!?]*\?\s*$"
)
TRAILING_LIST_NUMBER = re.compile(r"\n\s*[1-9]\d?\.\s*$")
SOURCE_REFERENCE = re.compile(r"\[\d{1,3}(?:\s*[,;\u2013-]\s*\d{1,3})*\]")


def unrequested_career_aside(text: str, request: str) -> bool:
    """Keep compensation and duration assertions out of an unrelated career answer."""
    if not re.search(r"\b(?:become|career|roadmap)\b", request, re.I):
        return False
    salary = bool(
        re.search(
            r"\b(?:salar(?:y|ies)|compensation)\b|[$\u00a3\u20ac]\s*\d|"
            r"\bearn\w*\b[^.!?\n]{0,60}\d",
            text,
            re.I,
        )
        and not re.search(r"\b(?:salar(?:y|ies)|compensation|pay|earn\w*|income)\b", request, re.I)
    )
    duration = bool(
        re.search(r"\b(?:learners?|beginners?|professionals?|developers?)\b", text, re.I)
        and re.search(r"\b\d+\s*(?:and\s*\d+\s*)?(?:months?|years?)\b", text, re.I)
        and not re.search(r"\b(?:long|duration|time|months?|years?)\b", request, re.I)
    )
    return salary or duration


def promotional(text: str) -> bool:
    """Catch third-party course pitches without excluding neutral training discussion."""
    return bool(
        CLUTTER.search(text)
        or BRANDED_COURSE.search(text)
        or (TRAINING.search(text) and PITCH.search(text))
    )


def future_years(text: str, year: int, request: str) -> set[int]:
    """Flag future wording unless the user explicitly requested that year."""
    requested = {int(value) for value in YEARS.findall(request)}
    return {int(value) for value in YEARS.findall(text) if int(value) > year} - requested


def adjacent_role(text: str, request: str) -> bool:
    """Do not strip an ML-role heading and present its body as AI-role requirements."""
    return bool(
        re.search(r"\bAI\s+engineer\b", request, re.I)
        and re.search(r"\b(?:machine learning|ML)\s+engineers?\b", text, re.I)
        and not re.search(r"\bAI\s+engineers?\b", text, re.I)
    )


def editorial_biography(text: str, request: str) -> bool:
    """Do not turn an author's background into requirements for the reader's role."""
    return bool(
        BIOGRAPHY.search(text)
        and not re.search(r"\b(?:author|biography|biographical|expert profile)\b", request, re.I)
    )


def display_issues(
    text: str, *, year: int, request: str, editorial: bool = True
) -> tuple[str, ...]:
    issues = []
    if promotional(text):
        issues.append("promotional, transcript or page-navigation text")
    if editorial and editorial_biography(text, request):
        issues.append("an author introduction or biography")
    if editorial and PAGE_HEADER.search(text):
        issues.append("publication header or byline text")
    if editorial and DEPENDENT_START.search(text.lstrip()):
        issues.append("a fragment that depends on missing preceding context")
    if editorial and (QUESTION_TAIL.search(text) or re.search(r"\?\s*\S", text)):
        issues.append("FAQ questions mixed with extracted text")
    if editorial and numbered_sections(text):
        issues.append("flattened numbered sections")
    if editorial and TRAILING_LIST_NUMBER.search(text):
        issues.append("a dangling number from the next list item")
    if editorial and SOURCE_REFERENCE.search(text):
        issues.append("a bibliography marker whose referenced material was not imported")
    if editorial and unrequested_career_aside(text, request):
        issues.append("unrequested compensation or learning-duration assertions")
    if TABLE.search(text) and not aligned_table(text):
        issues.append("table formatting that needs the original layout")
    if future_years(text, year, request):
        issues.append("future-dated wording outside the requested year")
    if adjacent_role(text, request):
        issues.append("an adjacent job role without an explicit link to the requested role")
    return tuple(issues)


def numbered_sections(text: str) -> tuple[tuple[int, int], ...]:
    """Recognize consecutive, independently headed items in a flattened list."""
    markers = list(re.finditer(r"(?<![\w.])([1-9]\d?)\.\s*(?=[A-Z]|$)", text))
    if len(markers) < 2 or any(
        int(right[1]) != int(left[1]) + 1 for left, right in zip(markers, markers[1:], strict=False)
    ):
        return ()
    starts = [0, *(marker.end() for marker in markers)]
    ends = [*(marker.start() for marker in markers), len(text)]
    sections = tuple(
        (
            start + len(text[start:end]) - len(text[start:end].lstrip()),
            start + len(text[start:end].rstrip()),
        )
        for start, end in zip(starts, ends, strict=True)
        if text[start:end].strip()
    )
    if len(sections) < 2 or not all(
        re.match(r"[A-Z][A-Za-z /&-]{1,60}\([^\n)]{1,80}\)", text[a:b]) for a, b in sections
    ):
        return ()
    return sections


def presentation_spans(text: str) -> Iterator[tuple[int, int]]:
    """Exact sentence/list spans, excluding a trailing FAQ question, with caveats intact."""
    tail = TRAILING_LIST_NUMBER.search(text)
    last = len(text[: tail.start()].rstrip()) if tail else len(text)
    if len(re.findall(r"\n\s*[1-9]\d?\.\s+[^.\n]{2,80}:", text[:last])) >= 2:
        # A role progression is useful as a whole list, including all qualifications.
        yield 0, last
        return
    for offset, stop in numbered_sections(text[:last]) or ((0, last),):
        block = text[offset:stop]
        spans = [(0, len(block))] if SCOPE.search(block) else readable_spans(block, 1)
        for a, b in spans:
            start, end = offset + a, offset + b
            question = QUESTION_TAIL.search(text[start:end])
            if question:
                end = start + len(text[start : start + question.start()].rstrip())
            dangling = TRAILING_LIST_NUMBER.search(text[start:end])
            if dangling:
                end = start + len(text[start : start + dangling.start()].rstrip())
            ordinal = re.search(r"(?<=[)\].])\s+\d{1,2}\.\s*$", text[start:end])
            previous = re.search(r"([1-9]\d?)\.\s*$", text[:start])
            next_item = re.search(r"\s+([1-9]\d?)\.\s*$", text[start:end])
            if (
                previous
                and next_item
                and int(next_item[1]) == int(previous[1]) + 1
                and re.match(
                    r"(?:Learn|Build|Deploy|Apply|Practice|Study|Create)\b", text[start:end]
                )
            ):
                ordinal = next_item
            if ordinal and re.match(
                r"(?:Learn|Build|Deploy|Apply|Practice|Study|Create)\b", text[end:].lstrip()
            ):
                end = start + ordinal.start()
            if end > start:
                yield start, end


def clean_spans(
    text: str, *, year: int, request: str, limit: int = 650
) -> Iterator[tuple[int, int]]:
    """Select exact whole sentences; never rewrite a table or remove a caveat."""
    if (
        future_years(text, year, request)
        or adjacent_role(text, request)
        or editorial_biography(text, request)
    ):
        return
    for start, end in presentation_spans(text):
        candidate = text[start:end]
        if (
            8 <= len(candidate) <= limit
            and not display_issues(candidate, year=year, request=request)
            and not (start and YEARS.search(text[:start]))
        ):
            yield start, end
