"""Bounded encyclopedia fallback through a fixed MediaWiki endpoint."""

import json

import httpx

from evidenceforge.retrieval.contracts import (
    RetrievalBatch,
    RetrievalFailure,
    RetrievalOptions,
    RetrievedSource,
)
from evidenceforge.schemas import SearchQuery


class WikipediaAdapter:
    name = "wikipedia"
    is_live = True
    retry_safe_categories: frozenset[str] = frozenset()

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owned = client is None
        self._client = client or httpx.AsyncClient(
            follow_redirects=False, trust_env=False, transport=httpx.AsyncHTTPTransport(retries=0)
        )

    async def aclose(self) -> None:
        if self._owned:
            await self._client.aclose()

    async def search(self, query: SearchQuery, options: RetrievalOptions) -> object:
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "generator": "search",
            "gsrsearch": query.text,
            "gsrlimit": str(min(options.max_results, 10)),
            "gsrnamespace": "0",
            "prop": "extracts|info",
            "explaintext": "1",
            "exintro": "1",
            "inprop": "url",
        }
        try:
            async with self._client.stream(
                "GET",
                "https://en.wikipedia.org/w/api.php",
                params=params,
                headers={"User-Agent": "EvidenceForge/0.1 (bounded research fallback)"},
                timeout=options.timeout_seconds,
            ) as response:
                if response.status_code != 200:
                    raise RetrievalFailure(
                        "rate_limit" if response.status_code == 429 else "provider"
                    )
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=16384):
                    if len(body) + len(chunk) > options.max_response_bytes:
                        raise RetrievalFailure("schema")
                    body.extend(chunk)
            data = json.loads(body)
            if not isinstance(data, dict) or "error" in data:
                raise RetrievalFailure("schema")
            pages = data.get("query", {}).get("pages", [])
            if not isinstance(pages, list) or len(pages) > options.max_results:
                raise RetrievalFailure("schema")
            results = tuple(
                RetrievedSource.model_validate(
                    {
                        "title": p["title"],
                        "url": p["fullurl"],
                        "content": p.get("extract", ""),
                        "content_scope": "search_excerpt",
                        "publisher": "Wikipedia",
                    }
                )
                for p in pages
            )
            return RetrievalBatch(results=results, search_credits=0.0)
        except httpx.TimeoutException as exc:
            raise RetrievalFailure("timeout") from exc
        except httpx.HTTPError as exc:
            raise RetrievalFailure("provider") from exc
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise RetrievalFailure("schema") from exc
