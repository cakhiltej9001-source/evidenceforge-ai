"""Tavily REST search through one fixed endpoint with streamed size limits."""

import json
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from math import isfinite

import httpx
from pydantic import SecretStr, ValidationError

from evidenceforge.retrieval.contracts import (
    RetrievalBatch,
    RetrievalFailure,
    RetrievalOptions,
    RetrievedSource,
)
from evidenceforge.schemas import SearchQuery


class TavilyAdapter:
    name = "tavily"
    is_live = True
    retry_safe_categories = frozenset({"rate_limit"})

    def __init__(self, api_key: SecretStr, client: httpx.AsyncClient | None = None) -> None:
        if not api_key.get_secret_value().strip():
            raise ValueError("Tavily API key is required.")
        self._key = api_key
        self._owned = client is None
        self._client = client or httpx.AsyncClient(
            follow_redirects=False,
            trust_env=False,
            transport=httpx.AsyncHTTPTransport(retries=0),
        )

    async def aclose(self) -> None:
        if self._owned:
            await self._client.aclose()

    async def search(self, query: SearchQuery, options: RetrievalOptions) -> object:
        payload = {
            "query": query.text,
            "search_depth": "basic",
            "topic": "general",
            "auto_parameters": False,
            "max_results": options.max_results,
            "include_answer": False,
            "include_raw_content": "text",
            "include_images": False,
            "include_usage": True,
        }
        if options.structured_domain_filters:
            domains = re.findall(r"(?<!\S)site:([a-zA-Z0-9.-]+)(?=\s|$)", query.text)
            if domains:
                domains = sorted(set(domain.casefold() for domain in domains))
                if len(domains) > 20:
                    raise RetrievalFailure("schema")
                payload["query"] = re.sub(
                    r"(?<!\S)site:[a-zA-Z0-9.-]+(?=\s|$)", "", query.text
                ).strip()
                if not payload["query"]:
                    raise RetrievalFailure("schema")
                payload["include_domains"] = domains
        try:
            async with self._client.stream(
                "POST",
                "https://api.tavily.com/search",
                json=payload,
                headers={"Authorization": f"Bearer {self._key.get_secret_value()}"},
                timeout=options.timeout_seconds,
            ) as response:
                if response.status_code in (401, 403):
                    raise RetrievalFailure("authentication")
                if response.status_code == 429:
                    hint = response.headers.get("Retry-After")
                    seconds: float | None = None
                    if hint is not None:
                        try:
                            seconds = float(hint)
                        except ValueError:
                            try:
                                seconds = max(
                                    0.0,
                                    (
                                        parsedate_to_datetime(hint) - datetime.now(UTC)
                                    ).total_seconds(),
                                )
                            except (TypeError, ValueError, OverflowError):
                                seconds = None
                    if seconds is not None and (not isfinite(seconds) or seconds < 0):
                        seconds = None
                    raise RetrievalFailure("rate_limit", seconds)
                if response.status_code != 200:
                    raise RetrievalFailure("provider")
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=16_384):
                    if len(body) + len(chunk) > options.max_response_bytes:
                        raise RetrievalFailure("schema")
                    body.extend(chunk)
            data = json.loads(body)
            if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                raise RetrievalFailure("schema")
            if len(data["results"]) > options.max_results:
                raise RetrievalFailure("schema")
            results = []
            for result in data["results"]:
                if not isinstance(result, dict):
                    raise RetrievalFailure("schema")
                raw = result.get("raw_content")
                full_text = isinstance(raw, str) and bool(raw.strip())
                content = raw if full_text else result.get("content", "")
                results.append(
                    RetrievedSource.model_validate(
                        {
                            "title": result.get("title"),
                            "url": result.get("url"),
                            "content": content,
                            "content_scope": "full_text" if full_text else "search_excerpt",
                        }
                    )
                )
            usage = data.get("usage")
            credits = usage.get("credits") if isinstance(usage, dict) else None
            return RetrievalBatch(results=tuple(results), search_credits=credits)
        except httpx.TimeoutException as exc:
            raise RetrievalFailure("timeout") from exc
        except httpx.HTTPError as exc:
            raise RetrievalFailure("provider") from exc
        except (ValueError, TypeError, ValidationError) as exc:
            raise RetrievalFailure("schema") from exc
