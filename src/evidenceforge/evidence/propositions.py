"""Conservative numeric extraction: all comparison dimensions must be explicit."""

import re
from datetime import date
from decimal import Decimal
from itertools import combinations
from typing import cast

from evidenceforge.evidence.contracts import Comparison, ComparisonRelationship, Proposition, Unit
from evidenceforge.identity import stable_id
from evidenceforge.schemas import EvidenceItem

# Deliberately narrow; ordinary prose is left unclassified, never called consistent.
PATTERN = re.compile(
    r"(?P<entity>[^.\n;]{1,120}?)\s+"
    r"(?P<metric>electricity output|energy output|installed capacity|capacity factor)"
    r"\s+was\s+(?P<value>-?\d{1,15}(?:\.\d{1,9})?)\s+"
    r"(?P<unit>TWh|GWh|MWh|kWh|Wh|GW|MW|kW|W|%)\s+in\s+"
    r"(?P<time>\d{4}(?:-\d{2}-\d{2})?)\s+for\s+"
    r"(?P<population>[^.\n;]{1,120}?)\s+under\s+(?P<conditions>[^.\n;]{1,120})"
    r"(?=\.(?:\s|$)|$)",
    re.IGNORECASE | re.MULTILINE,
)
UNITS = {
    "Wh": ("Wh", Decimal(1)),
    "kWh": ("Wh", Decimal(1000)),
    "MWh": ("Wh", Decimal(1000000)),
    "GWh": ("Wh", Decimal(1000000000)),
    "TWh": ("Wh", Decimal(1000000000000)),
    "W": ("W", Decimal(1)),
    "kW": ("W", Decimal(1000)),
    "MW": ("W", Decimal(1000000)),
    "GW": ("W", Decimal(1000000000)),
    "%": ("%", Decimal(1)),
}


def norm(text: str) -> str:
    return " ".join(text.casefold().split())


def extract(item: EvidenceItem) -> tuple[Proposition, ...]:
    results = []
    for match in PATTERN.finditer(item.passage):
        try:
            date.fromisoformat(
                match["time"] if len(match["time"]) > 4 else match["time"] + "-01-01"
            )
        except ValueError:
            continue
        # Trim whitespace without changing the exact retained span.
        start = match.start() + len(match.group()) - len(match.group().lstrip())
        end = match.end()
        unit = match["unit"]
        if unit not in UNITS:
            continue
        results.append(
            Proposition(
                id=stable_id("proposition", item.id, start, end, "scoped_numeric_v1"),
                evidence_id=item.id,
                question_ids=tuple(sorted(item.question_ids)),
                start_offset=start,
                end_offset=end,
                quote=item.passage[start:end],
                entity=norm(match["entity"]),
                metric=norm(match["metric"]),
                timeframe=match["time"],
                population=norm(match["population"]),
                conditions=norm(match["conditions"]),
                value=Decimal(match["value"]),
                unit=cast(Unit, unit),
            )
        )
    return tuple(results)


def compare(left: Proposition, right: Proposition) -> Comparison:
    left, right = sorted((left, right), key=lambda p: p.id)
    questions = tuple(sorted(set(left.question_ids) & set(right.question_ids)))
    if not questions:
        raise ValueError("propositions must share a question")
    different = [
        name
        for name in ("entity", "metric", "timeframe", "population", "conditions")
        if getattr(left, name) != getattr(right, name)
    ]
    lu, lm = UNITS[left.unit]
    ru, rm = UNITS[right.unit]
    values: dict[str, str] = {}
    relationship: ComparisonRelationship
    if different or lu != ru:
        relationship = "not_comparable"
        rationale = (
            "Different "
            + ", ".join(different + (["unit dimension"] if lu != ru else []))
            + "; no contradiction inferred."
        )
    else:
        lv, rv = left.value * lm, right.value * rm
        relationship = "supports" if lv == rv else "contradicts"
        rationale = (
            "Equal numeric values after unit conversion under the same explicit scope."
            if lv == rv
            else "Unequal numeric values under the same scope; unresolved without a vote decision."
        )
        values = {"normalized_left": str(lv), "normalized_right": str(rv), "canonical_unit": lu}
        if norm(left.quote) == norm(right.quote):
            relationship = "duplicate"
            rationale = (
                "Identical normalized quotation; independent corroboration is not established."
            )
    return Comparison(
        id=stable_id("comparison", left.id, right.id),
        left_id=left.id,
        right_id=right.id,
        question_ids=questions,
        relationship=relationship,
        rationale=rationale,
        normalized_left=values.get("normalized_left"),
        normalized_right=values.get("normalized_right"),
        canonical_unit=values.get("canonical_unit"),
    )


def compare_all(
    propositions: tuple[Proposition, ...], limit: int
) -> tuple[tuple[Comparison, ...], bool]:
    results: list[Comparison] = []
    for left, right in combinations(sorted(propositions, key=lambda p: p.id), 2):
        if not set(left.question_ids) & set(right.question_ids):
            continue
        if len(results) == limit:
            return tuple(results), True
        results.append(compare(left, right))
    return tuple(results), False
