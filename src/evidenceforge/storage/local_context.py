"""Combine authorized document metadata and context-only generated report references."""

from evidenceforge.identity import stable_id
from evidenceforge.planning import ContextBatch
from evidenceforge.schemas import ContextReference
from evidenceforge.storage.documents import DocumentFailure, DocumentStore
from evidenceforge.storage.reports import ReportRepository


class LocalContextRepository:
    def __init__(self, documents: DocumentStore, reports: ReportRepository) -> None:
        self.documents, self.reports = documents, reports

    async def select(
        self,
        *,
        owner_scope: str,
        document_ids: tuple[str, ...],
        include_prior_reports: bool,
        limit: int,
    ) -> object:
        references = []
        for identifier in document_ids[:limit]:
            try:
                document = self.documents.get(owner_scope, identifier)
            except DocumentFailure:
                continue
            if document.chunk_count:
                references.append(
                    ContextReference(
                        id=stable_id("context", owner_scope, "document", identifier),
                        owner_scope=owner_scope,
                        kind="document",
                        target_id=identifier,
                    )
                )
        if include_prior_reports and len(references) < limit:
            references.extend(
                ContextReference(
                    id=stable_id("context", owner_scope, "prior_report", report.id),
                    owner_scope=owner_scope,
                    kind="prior_report",
                    target_id=report.id,
                )
                for report in self.reports.list(owner_scope, limit=limit - len(references))
            )
        return ContextBatch(references=tuple(references))
