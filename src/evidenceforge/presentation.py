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
    r"\b(?:not|never|no longer|formerly|until|if|unless|however|but|except|"
    r"excludes?|excluding|only|may|might|could|disputed|incorrect|outdated|"
    r"false|untrue|wrong|misleading|inaccurate|unverified|uncertain)\b",
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


def promotional(text: str) -> bool:
    """Catch third-party course pitches without excluding neutral training discussion."""
    return bool(CLUTTER.search(text) or (TRAINING.search(text) and PITCH.search(text)))


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


def display_issues(text: str, *, year: int, request: str) -> tuple[str, ...]:
    issues = []
    if promotional(text):
        issues.append("promotional, transcript or page-navigation text")
    if TABLE.search(text) and not aligned_table(text):
        issues.append("table formatting that needs the original layout")
    if future_years(text, year, request):
        issues.append("future-dated wording outside the requested year")
    if adjacent_role(text, request):
        issues.append("an adjacent job role without an explicit link to the requested role")
    return tuple(issues)


def clean_spans(
    text: str, *, year: int, request: str, limit: int = 650
) -> Iterator[tuple[int, int]]:
    """Select exact whole sentences; never rewrite a table or remove a caveat."""
    if future_years(text, year, request) or adjacent_role(text, request):
        return
    spans = [(0, len(text))] if SCOPE.search(text) else readable_spans(text, 1)
    for start, end in spans:
        candidate = text[start:end]
        if (
            8 <= len(candidate) <= limit
            and not display_issues(candidate, year=year, request=request)
            and not re.match(r"^(?:it|this|that|these|those|they|he|she|there)\b", candidate, re.I)
            and not (start and YEARS.search(text[:start]))
        ):
            yield start, end
