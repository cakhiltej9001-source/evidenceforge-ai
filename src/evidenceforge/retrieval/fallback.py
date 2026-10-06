"""Ordered providers; each attempt is accounted for by SourceProcessor."""

from evidenceforge.retrieval.contracts import RetrievalAdapter, RetrievalOptions
from evidenceforge.schemas import SearchQuery


class OrderedSearch:
    name = "ordered_search"
    retry_safe_categories: frozenset[str] = frozenset()

    def __init__(self, providers: tuple[RetrievalAdapter, ...]) -> None:
        if not providers or len({p.name for p in providers}) != len(providers):
            raise ValueError("Providers must be nonempty and uniquely named.")
        self.providers = providers
        self.is_live = any(p.is_live for p in providers)

    async def search(self, query: SearchQuery, options: RetrievalOptions) -> object:
        raise RuntimeError("Ordered providers require individual budget reservations.")
