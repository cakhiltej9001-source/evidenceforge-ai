"""Read-only GB half-hour generation mix from one fixed NESO endpoint."""

import json
from datetime import timedelta
from typing import Annotated, Literal, Self

import httpx
from pydantic import AwareDatetime, Field, FiniteFloat, HttpUrl, ValidationError, model_validator

from evidenceforge.identity import stable_id
from evidenceforge.retrieval.contracts import (
    RetrievalBatch,
    RetrievalFailure,
    RetrievalOptions,
    RetrievedSource,
)
from evidenceforge.schemas import Contract, SearchQuery, SourceType

ENDPOINT = "https://api.carbonintensity.org.uk/generation"
Fuel = Literal["gas", "coal", "biomass", "nuclear", "hydro", "imports", "other", "wind", "solar"]
FUELS = frozenset(
    {"gas", "coal", "biomass", "nuclear", "hydro", "imports", "other", "wind", "solar"}
)


class FuelShare(Contract):
    fuel: Fuel
    perc: Annotated[FiniteFloat, Field(strict=True, ge=0, le=100)]


class GenerationPeriod(Contract):
    start: AwareDatetime = Field(alias="from")
    end: AwareDatetime = Field(alias="to")
    generationmix: Annotated[tuple[FuelShare, ...], Field(min_length=9, max_length=9)]

    @model_validator(mode="after")
    def complete_period(self) -> Self:
        if self.end - self.start != timedelta(minutes=30):
            raise ValueError("Expected a half-hour period")
        if {item.fuel for item in self.generationmix} != FUELS:
            raise ValueError("Expected all nine unique fuel categories")
        if abs(sum(item.perc for item in self.generationmix) - 100) > 0.6:
            raise ValueError("Fuel shares must sum to 100 within rounding tolerance")
        return self


class GenerationResponse(Contract):
    # Official example uses a single-item array; the live endpoint also uses an object.
    data: (
        GenerationPeriod
        | Annotated[tuple[GenerationPeriod, ...], Field(min_length=1, max_length=1)]
    )

    @property
    def period(self) -> GenerationPeriod:
        return self.data if isinstance(self.data, GenerationPeriod) else self.data[0]


def as_batch(
    response: GenerationResponse, *, fixture: bool = False, source_type: SourceType = SourceType.WEB
) -> RetrievalBatch:
    if source_type not in (SourceType.WEB, SourceType.API):
        raise RetrievalFailure("schema")
    period = response.period
    interval = f"{period.start.isoformat()} to {period.end.isoformat()}"
    label = "Synthetic fixture: " if fixture else "API-derived record: "
    shares = sorted(
        period.generationmix, key=lambda item: (item.fuel not in {"solar", "wind"}, item.fuel)
    )
    paragraphs = [
        f"{label}Great Britain {item.fuel} electricity generation share was {item.perc:g}% "
        f"for the half-hour period {interval}."
        for item in shares
    ]
    paragraphs.append(
        f"{label}Percentages describe generation mix including imports, not absolute electricity "
        "output in MWh, annual totals, installed capacity or global performance."
    )
    # Retain the validated provider values alongside their deterministic textual projection.
    paragraphs.append("Validated API payload:\n" + response.model_dump_json(by_alias=True))
    return RetrievalBatch(
        results=(
            RetrievedSource(
                title=("Synthetic GB generation mix" if fixture else "NESO GB generation mix")
                + f" ({interval})",
                url=HttpUrl(ENDPOINT),
                source_type=source_type,
                publisher="Synthetic fixture" if fixture else "National Energy System Operator",
                # The interval endpoint is not a verified publication timestamp.
                publication_date=None,
                source_family=stable_id(
                    "source_family", "fixture" if fixture else "neso_generation"
                ),
                content="\n\n".join(paragraphs),
            ),
        ),
    )


class CarbonIntensityAdapter:
    name = "carbon_intensity"
    is_live = True
    retry_safe_categories: frozenset[str] = frozenset()

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owned = client is None
        self._client = client or httpx.AsyncClient(
            follow_redirects=False,
            trust_env=False,
            transport=httpx.AsyncHTTPTransport(retries=0),
        )

    async def aclose(self) -> None:
        if self._owned:
            await self._client.aclose()

    async def search(self, query: SearchQuery, options: RetrievalOptions) -> RetrievalBatch:
        # Query text is used by downstream relevance admission, never interpolated into URLs.
        try:
            async with self._client.stream(
                "GET",
                ENDPOINT,
                headers={"Accept": "application/json"},
                timeout=options.timeout_seconds,
                follow_redirects=False,
            ) as response:
                if response.status_code == 429:
                    raise RetrievalFailure("rate_limit")
                if response.status_code in {401, 403}:
                    raise RetrievalFailure("authentication")
                if response.status_code != 200:
                    raise RetrievalFailure("provider")
                if "application/json" not in response.headers.get("Content-Type", "").lower():
                    raise RetrievalFailure("schema")
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=16_384):
                    if len(body) + len(chunk) > options.max_response_bytes:
                        raise RetrievalFailure("schema")
                    body.extend(chunk)
            parsed = GenerationResponse.model_validate(json.loads(body))
            batch = as_batch(parsed, source_type=query.source_type)
            if len(batch.results[0].content.encode()) > options.max_source_bytes:
                raise RetrievalFailure("schema")
            return batch
        except httpx.TimeoutException:
            raise RetrievalFailure("timeout") from None
        except httpx.HTTPError:
            raise RetrievalFailure("provider") from None
        except (ValueError, TypeError, ValidationError):
            raise RetrievalFailure("schema") from None


class CarbonIntensityFixture:
    name = "carbon_intensity_fixture"
    is_live = False

    async def search(self, query: SearchQuery, options: RetrievalOptions) -> RetrievalBatch:
        shares = dict(
            gas=40, coal=0, biomass=5, nuclear=15, hydro=2, imports=10, other=1, wind=20, solar=7
        )
        return as_batch(
            GenerationResponse.model_validate(
                {
                    "data": {
                        "from": "2026-01-01T12:00Z",
                        "to": "2026-01-01T12:30Z",
                        "generationmix": [
                            {"fuel": fuel, "perc": share} for fuel, share in shares.items()
                        ],
                    }
                }
            ),
            fixture=True,
            source_type=query.source_type,
        )
