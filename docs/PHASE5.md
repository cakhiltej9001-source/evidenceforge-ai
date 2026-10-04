# Phase 5: local documents and workflow persistence

Implemented 1 October 2026. PDF/DOCX/TXT documents are parsed and retrieved locally. The reasoning
adapter remains an explicitly labeled offline fixture. No live model or web search was run.

## Local document demo

Run from the project directory in PowerShell:

```powershell
cd "C:\Users\AKHILTEJ\Documents\ChatGPT\AI Research agent"
uv run --locked evidenceforge-ingest tests/fixtures/documents/energy.txt --owner demo
```

Copy the printed `id` into this command:

```powershell
uv run --locked evidenceforge-research "Compare solar and wind electricity output." --owner demo --document DOCUMENT_ID
```

`--document` can be repeated. Use the same owner and data directory for ingestion and research.
Default data is ignored `.evidenceforge`; both commands accept `--data-dir`.
A document request uses only local document retrieval by default. Without documents, the existing
synthetic web fixture demo remains available. A caller can inject explicitly configured adapters.

## Pause and resume in separate processes

```powershell
uv run --locked evidenceforge-research "Compare solar and wind electricity output." --demo second-pass --pause-after source_processor
```

The command prints the saved `thread_id`. Resume it, using the same data directory and owner:

```powershell
uv run --locked evidenceforge-research --resume THREAD_ID --owner local
```

Pause boundaries are `query_generator`, `source_processor` and `evidence_extractor`.
These are controlled developer demo boundaries, not Phase 8 approval/edit/cancel interrupts.
A pause keeps `run_status=running` and leaves pending steps in the SQLite checkpoint. No final
report is announced until finalization and output delivery. Resume reconstructs the graph and invokes
it with no new input, so Manager/Planner and already completed retrieval batches are not restarted.
The stored request and budgets are authoritative. A new question always creates fresh run/thread IDs.
Changing adapter classes, context/model classes or graph/retrieval options refuses resume.
Injected fixture payloads and custom adapter behavior must remain compatible; their opaque internal
configuration is not inferred or guaranteed by the stored class/options profile.

## Parsed text and citation locations

DocumentStore validates extension, input bytes, page/unit/chunk counts, extracted text, archive/page
expansion and per-owner stored original bytes. It registers a content-addressed owner-scoped ID and
retains original bytes, their SHA-256, canonical extracted text and located chunks in SQLite.
Chunk defaults are 1000 characters with 100-character overlap, contained within one located unit.
They are configurable baseline settings, not an optimized recall claim.

- PDF: one-based page locations. Textless pages are recorded as possibly scanned or blank, with
  **OCR unavailable**. Mixed files retain text-bearing pages and disclose missing pages. Encrypted
  PDFs are refused. Extraction layout can differ from the page's visual reading order.
- DOCX: one-based body paragraph/table-cell order, with row/column sections for table cells.
  Headers, footers, drawings, nested tables and tracked-change text are not indexed. Page numbers
  are not invented because DOCX pagination depends on rendering.
- TXT: UTF-8/UTF-8-BOM, blank-line-separated paragraph locations. Other encodings and NUL-bearing
  content are refused.

Offsets into a retained evidence snapshot are separate from offsets into the canonical parsed
document. Canonical text joins nonempty located units with blank lines. Neither is a PDF binary-byte
locator. Sources retain document ID, original binary hash, chunk ID and acquisition dates; reports
show page/paragraph locations and source hashes/dates. Hashes and chunk metadata detect corruption.
Citation audits still verify exact retained quotations, not independent factual truth.

Parsers operate in the local process with bounded input/output policy. PDF decompression/parsing
can allocate memory before expansion checks; these limits are not an OS-level CPU/memory sandbox.
Only read-only retrieval is exposed. Document instructions do not gain application tools.

## Scoping, state and memory

| Store | Location | Purpose |
|---|---|---|
| Documents/chunks | documents/documents.sqlite | Owned original documents and located lexical index |
| Workflow checkpoints | checkpoints/<owner hash>/workflow.sqlite | Full graph state, pending steps and thread history |
| Run registration | checkpoints/<owner hash>/runs.sqlite | Immutable request/budget/configuration identity |
| Search receipts | calls/ | Operation reservations and durable outcome reuse |
| Prior reports | memory/reports.sqlite | Selected generated summaries and evidence/source navigation IDs |
| Exported results | reports/<run_id>/ | Final Markdown and inspection JSON |

Owner scope and requested document IDs are checked on context selection, lexical lookup and source
admission, including cached outcomes. Scope names are local access boundaries, not authenticated
accounts; public service authentication remains later work. Files/databases are local and unencrypted,
excluded from Git. Summaries are owner-filtered and bounded on retrieval. Generated reports remain
context-only: they cannot be passed through the document index as independent evidence.

The SQLite async saver is opened and closed around each service invocation. Per-thread OS locks
reject a second active writer and release when the process exits. Resume validates checkpoint
identity/request against the registration. Terminal resume redelivers the same result without research.
Reports are exported atomically per file and saved idempotently in the separate memory repository.
A crash before checkpointing can re-execute a node. Search operation receipts reuse completed calls
and disclose uncertain pending outcomes; fixture reasoning is replayable. Exactly-once paid model
execution is not claimed. Checkpoint retention/deletion and consolidated guardrails remain later work.

## Verification and dependencies

Tests execute TXT/PDF/DOCX extraction and located reports; scanned/blank and encrypted cases;
invalid/oversized/corrupt input; overlapping spans; owner/request filters; separate report memory;
fresh state; terminal replay; configuration/foreign-thread rejection; locks; separate-thread isolation;
source-file replacement after retrieval; and actual pause/resume in two Python processes.
PROGRESS.md records exact final gate results.

Tested additions: pypdf 6.19.0, python-docx 1.2.0, langgraph-checkpoint-sqlite 3.1.1,
aiosqlite 0.22.1 and lxml 6.1.3. sqlite-vec 0.1.9 is a transitive checkpointer dependency;
no vector index, embeddings or vector retrieval are implemented or used.

API checks: [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
distinguishes thread checkpoints from application stores;
[SQLite saver implementation](https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint-sqlite)
and installed code confirmed the async lifecycle;
[pypdf extraction guidance](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
explains textless pages and extraction limits;
[python-docx document guidance](https://python-docx.readthedocs.io/en/latest/user/documents.html)
and installed 1.2.0 interfaces were inspected before implementation.

## Next phase

Phase 6 adds graph projection, source ranking and contradiction-aware research. It has not started.
The original assignment PDF and companion instructions remain unavailable; assignment mapping is
provisional and overall assignment completion is not claimed.