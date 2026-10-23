"""Conservative detail checks for criteria that explicitly request an inventory.

These checks can withhold support; they cannot establish truth or semantic completeness.
The structured model still decides whether each retained item answers the criterion.
"""

import re
from collections.abc import Iterable

_ACTION = re.compile(
    r"\b(?:list|lists|name|names|identify|identifies|enumerate|specify|describe|provide|give)\b",
    re.I,
)
_CATEGORY = re.compile(
    r"\b(?:foundations|skills|topics|methods|techniques|types|kinds|languages|frameworks|"
    r"libraries|sources|gases|components|steps|examples|options|requirements|causes|"
    r"factors|applications|projects?|metrics|roles|pathways|concepts)\b",
    re.I,
)
_INTRO = re.compile(
    r"\b(?:includes?|included|including|such as|like|namely|comprises?|comprising|"
    r"consists? of|consisting of|contains?|are|is)\b|:",
    re.I,
)
_ABSENCE = re.compile(
    r"\b(?:missing|unavailable|absent|unreported|not provided|not reported)\b", re.I
)
_WORDS = re.compile(r"[a-z][a-z0-9+#]*", re.I)
_COUNTS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
_GENERIC = frozenset(
    "a an and or the of in on for to as with by from these those their this that which "
    "list lists name names identify identifies enumerate specify describe provide give "
    "essential core key basic important distinct different main major relevant required "
    "necessary needed useful include includes including such like comprise comprises "
    "consist consists contains contain are is be used use can must should all various "
    "foundation concept skill topic method technique type kind language framework library source "
    "gas component step example option requirement cause factor application project "
    "metric role pathway knowledge understanding ability proficiency strong solid "
    "advanced fundamental technical professional practical enough etc "
    "one two three four five six".split()
)


def _tokens(text: str) -> set[str]:
    aliases = {
        "atmospheric": "atmosphere",
        "mathematics": "math",
        "mathematical": "math",
        "maths": "math",
        "statistical": "statistic",
        "exercise": "project",
        "exercises": "project",
        "portfolio": "project",
    }
    result = set()
    for word in _WORDS.findall(text.casefold()):
        token = aliases.get(word, word)
        if token.endswith("ies"):
            token = token[:-3] + "y"
        elif token.endswith("s") and not token.endswith(("ss", "is")):
            token = token[:-1]
        result.add(token)
    return result


def _items(text: str, criterion_words: set[str]) -> set[str]:
    """Count distinct named phrases, excluding a restatement of the category."""
    result = set()
    for item in re.split(r"\s*(?:[,;]|\b(?:and|or)\b|\n\s*(?:[-*\u2022]|\d+[.)]))\s*", text):
        words = _tokens(item)
        # Long narrative clauses and category-only mentions do not name list members.
        if 0 < len(words) <= 12 and words - criterion_words - _GENERIC:
            result.add(" ".join(sorted(words - _GENERIC)))
    return result


def enumerative_support(criterion: str, passages: Iterable[str]) -> bool:
    """Require concrete listed detail when an inventory is explicitly requested.

    A category occurring as one member of a broader list is not an inventory of
    that category. Nearby unrelated lists also cannot satisfy it. Unmarked short
    lists remain eligible when no generic category mention competes with them;
    their subject relevance remains the structured model's responsibility.
    """
    if (
        not _ACTION.search(criterion[:80])
        or not _CATEGORY.search(criterion)
        or _ABSENCE.search(criterion)
    ):
        return True
    count_match = re.search(r"\b([1-9]|one|two|three|four|five|six)\b", criterion, re.I)
    minimum = (
        int(count_match[0])
        if count_match and count_match[0].isdigit()
        else _COUNTS[count_match[0].casefold()]
        if count_match
        else 2
    )
    head = re.split(
        r"\b(?:required|needed|used|for|to|that|which)\b", criterion, maxsplit=1, flags=re.I
    )[0]
    criterion_words = _tokens(criterion)
    # Keep category nouns for header matching, and meaningful modifiers such as
    # "mathematical". Drop generic wording, not the requested subject.
    categories = _tokens(" ".join(_CATEGORY.findall(head)))
    scope = (_tokens(head) - _GENERIC) | categories
    broad = {
        "foundation",
        "concept",
        "skill",
        "topic",
        "method",
        "technique",
        "type",
        "kind",
        "step",
        "example",
        "option",
        "requirement",
        "factor",
    }
    specific = scope - broad
    if specific:
        scope = specific
    named: set[str] = set()
    for passage in passages:
        sentences = re.split(r"(?<=[.!?])\s+|\n\s*\n", passage)
        for sentence in sentences:
            scoped = False
            for intro in _INTRO.finditer(sentence):
                before, after = sentence[: intro.start()], sentence[intro.end() :]
                if _tokens(before) & scope:
                    named.update(_items(after, criterion_words))
                    scoped = True
                if intro[0].casefold() in {"are", "is"} and _tokens(after) & scope:
                    named.update(_items(before, criterion_words))
                    scoped = True
            if (
                not scoped
                and not (_tokens(passage) & scope)
                and not _INTRO.search(sentence)
                and re.search(r"[,;]|\b(?:and|or)\b", sentence)
            ):
                # A model-selected bare enumeration can be valid without repeating
                # its header. Do not infer a subject for an explicitly different list.
                named.update(_items(sentence, criterion_words))
    return len(named) >= minimum
