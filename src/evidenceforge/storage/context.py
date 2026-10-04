"""Owner-scoped context metadata selection, with no document content or ingestion."""

from typing import Protocol

from evidenceforge.planning import ContextBatch
from evidenceforge.schemas import ContextReference


class ContextRepository(Protocol):
    async def select(
        self,
        *,
        owner_scope: str,
        document_ids: tuple[str, ...],
        include_prior_reports: bool,
        limit: int,
    ) -> object: ...


class InMemoryContextRepository:
    def __init__(self, references: tuple[ContextReference, ...] = ()) -> None:
        validated = tuple(ContextReference.model_validate(reference) for reference in references)
        if len({reference.id for reference in validated}) != len(validated):
            raise ValueError("context repository IDs must be unique")
        self._references = validated

    async def select(
        self,
        *,
        owner_scope: str,
        document_ids: tuple[str, ...],
        include_prior_reports: bool,
        limit: int,
    ) -> object:
        selected = [
            reference
            for reference in self._references
            if reference.owner_scope == owner_scope
            and (
                (reference.kind == "document" and reference.target_id in document_ids)
                or (reference.kind == "prior_report" and include_prior_reports)
            )
        ]
        selected.sort(key=lambda reference: (reference.kind, reference.target_id, reference.id))
        return ContextBatch(references=tuple(selected[:limit]))
