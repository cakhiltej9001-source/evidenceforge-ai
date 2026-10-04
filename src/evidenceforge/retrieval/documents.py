"""Read-only lexical retrieval restricted to the current request's owned documents."""

from evidenceforge.retrieval.contracts import (
    RetrievalBatch,
    RetrievalFailure,
    RetrievalOptions,
    RetrievedDocument,
)
from evidenceforge.schemas import SearchQuery
from evidenceforge.storage.documents import DocumentFailure, DocumentStore


class DocumentRetrievalAdapter:
    name = "local_documents"
    is_live = False

    def __init__(
        self, store: DocumentStore, owner_scope: str, document_ids: tuple[str, ...]
    ) -> None:
        self.store, self.owner_scope, self.document_ids = store, owner_scope, document_ids
        self.calls = 0

    async def search(self, query: SearchQuery, options: RetrievalOptions) -> object:
        self.calls += 1
        try:
            chunks = self.store.search(
                self.owner_scope, self.document_ids, query.text, options.max_results
            )
            return RetrievalBatch(
                results=tuple(
                    RetrievedDocument(
                        title=self.store.get(self.owner_scope, chunk.document_id).title,
                        owner_scope=self.owner_scope,
                        document_id=chunk.document_id,
                        document_hash=self.store.get(
                            self.owner_scope, chunk.document_id
                        ).binary_hash,
                        chunk_id=chunk.id,
                        content=chunk.text,
                        document_start_offset=chunk.start_offset,
                        document_end_offset=chunk.end_offset,
                        page=chunk.page,
                        paragraph=chunk.paragraph,
                        section=chunk.section,
                    )
                    for chunk in chunks
                )
            )
        except DocumentFailure as exc:
            raise RetrievalFailure("provider") from exc
