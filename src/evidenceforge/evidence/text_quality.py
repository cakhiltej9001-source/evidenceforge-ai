"""Bounded layout and absence checks; these are not general semantic verification."""

import re
from collections.abc import Iterable, Iterator

from evidenceforge.nodes.extraction import readable_spans, spans

ABSENCE = re.compile(
    r"\b(?:missing|unavailable|absent|unreported|not\s+(?:provided|reported))\b", re.I
)
NEGATED_ABSENCE = re.compile(
    r"\b(?:not|never)\s+(?:missing|unavailable|absent|unreported)\b"
    r"|\bno\s+(?:(?:data|values|percentages)\s+(?:are|were)\s+)?missing\b",
    re.I,
)
EXERCISE = re.compile(r"\b(?:Problem|Question|Exercise)\s+\d+\s*[-:.\u2013\u2014]", re.I)
GENERIC = frozenset(
    "a an the and or of in on for to by from with any all each which what "
    "explicitly state list identify describe give provide report requested "
    "missing unavailable absent unreported not provided reported data datum "
    "primary gas gases percentage percentages percent value values inventory "
    "source sources text retained information measurement measurements are is "
    "was were has have be been".split()
)


def aligned_table(text: str) -> bool:
    """Accept only explicit delimiters and a consistent header/row width."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    delimiter = "\t" if all("\t" in line for line in lines) else "|"
    if not all(delimiter in line for line in lines):
        return False
    rows = [[cell.strip() for cell in line.strip("|").split(delimiter)] for line in lines]
    width = len(rows[0])
    if width < 2 or any(len(row) != width for row in rows):
        return False
    if any(not re.search(r"[A-Za-z]", cell) for cell in rows[0]):
        return False
    data = rows[1:]
    if all(re.fullmatch(r":?-{3,}:?", cell) for cell in data[0]):
        data = data[1:]
    return bool(data) and all(all(cell for cell in row) for row in data)


def ambiguous_flat_table(text: str) -> bool:
    """Line breaks and inconsistent delimiters do not restore lost columns."""
    if aligned_table(text):
        return False
    flattened = " ".join(text.replace("|", " ").split())
    values = list(re.finditer(r"(?<![\w.])<?\s*\d+(?:[.,]\d+)?\s*%?", flattened))
    total_percentages = 0
    run_count = run_percentages = 0
    previous_end = 0
    for match in values:
        if flattened[previous_end : match.start()].strip():
            if run_count >= 3:
                total_percentages += run_percentages
            run_count = run_percentages = 0
        run_count += 1
        run_percentages += "%" in match.group()
        previous_end = match.end()
    if run_count >= 3:
        total_percentages += run_percentages
    return total_percentages >= 6


def quality_spans(text: str, size: int) -> Iterator[tuple[int, int]]:
    """Keep table layout atomic; an exercise ends at its paragraph boundary."""
    for start, end in spans(text, max(1, len(text))):
        paragraph = text[start:end]
        marker = EXERCISE.search(paragraph)
        if marker:
            for left, right in readable_spans(paragraph[: marker.start()], size):
                yield start + left, start + right
            yield start + marker.start(), end
        elif aligned_table(paragraph) or ambiguous_flat_table(paragraph):
            yield start, end
        else:
            for left, right in readable_spans(paragraph, size):
                yield start + left, start + right


def absence_supported(criterion: str, statements: Iterable[str]) -> bool:
    """Require criterion subject words in the same clause as an absence statement."""
    anchors = set(re.findall(r"[a-z]+", criterion.casefold())) - GENERIC
    for statement in statements:
        for clause in re.split(r"(?<=[.!?;])\s+|\n", statement):
            if not ABSENCE.search(clause) or NEGATED_ABSENCE.search(clause):
                continue
            if anchors.issubset(set(re.findall(r"[a-z]+", clause.casefold()))):
                return True
    return False
