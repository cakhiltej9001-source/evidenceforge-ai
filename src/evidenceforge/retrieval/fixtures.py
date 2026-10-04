"""Synthetic public corpus and scripted responses; no external search."""

from copy import deepcopy

from pydantic import HttpUrl

from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievalOptions, RetrievedSource
from evidenceforge.schemas import SearchQuery


class FixtureRetrievalAdapter:
    name = "fixture"
    is_live = False

    def __init__(self, response: object = None) -> None:
        self.response = response
        self.calls = 0

    async def search(self, query: SearchQuery, options: RetrievalOptions) -> object:
        self.calls += 1
        if self.response is not None:
            return deepcopy(self.response)
        return RetrievalBatch(
            results=(
                RetrievedSource(
                    title="Synthetic energy fixture",
                    url=HttpUrl("https://example.org/fixtures/energy"),
                    content=(
                        "Synthetic fixture: solar electricity output depends on sunlight.\n\n"
                        "Synthetic fixture: wind electricity output depends on wind speed.\n\n"
                        "Synthetic fixture limitations: these are examples, not real measurements."
                    ),
                ),
            )
        )


class SecondPassFixture(FixtureRetrievalAdapter):
    async def search(self, query: SearchQuery, options: RetrievalOptions) -> object:
        self.calls += 1
        topic = "solar" if query.research_pass == 1 else "wind"
        condition = "sunlight" if topic == "solar" else "wind speed"
        return RetrievalBatch(
            results=(
                RetrievedSource(
                    title=f"Synthetic {topic} fixture",
                    url=HttpUrl(f"https://example.org/fixtures/{topic}"),
                    content=(
                        f"Synthetic fixture: {topic} electricity output depends on {condition}."
                    ),
                ),
            )
        )


class DisputeFixture(FixtureRetrievalAdapter):
    """Synthetic differing numbers plus scope/unit/copy examples, never real measurements."""

    async def search(self, query: SearchQuery, options: RetrievalOptions) -> object:
        self.calls += 1

        def source(
            name: str,
            value: str,
            unit: str = "GWh",
            year: str = "2024",
            primary: bool = False,
            family: str | None = None,
        ) -> RetrievedSource:
            return RetrievedSource(
                title="Synthetic " + name,
                url=HttpUrl(f"https://{name}.example.org/energy"),
                content=(
                    f"Northfield solar electricity output was {value} {unit} in {year} "
                    "for all plants under standard operation."
                ),
                publisher="Synthetic " + name,
                publication_date="2025-01-01" if primary else "2026-09-01",
                primary_evidence=primary,
                methodology_transparent=primary,
                metadata_rationale="Synthetic metadata; publisher assessment is unverified.",
                source_family=family,
            )

        primary = source("primary", "100", primary=True, family="family_primary")
        secondary = source("secondary", "120", family="family_secondary")
        results: tuple[RetrievedSource, ...] = (primary, secondary)
        if query.research_pass > 1:
            results += (
                source("units", "100000", unit="MWh", primary=True, family="family_units"),
                source("historical", "900", year="2023", family="family_historical"),
                source("copy", "100", family="family_primary"),
            )
        return RetrievalBatch(results=results[: options.max_results])
