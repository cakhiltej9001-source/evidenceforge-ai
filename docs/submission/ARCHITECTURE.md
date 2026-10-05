# Architecture

This diagram follows the implemented Phase 8 graph and service boundary.
The input review runs before graph invocation. Provider clients, repository
connections and runtime workers are injected outside serialized state.

```mermaid
flowchart TD
  UI[Streamlit UI or CLI] --> SERVICE[ResearchService input review]
  SERVICE -->|Accepted request| M[Manager]
  SERVICE -->|Clarify or reject| HELP[Bounded input decision]
  M --> P[Planner]
  M --> C[Context manager]
  P --> JOIN[All-predecessor join]
  C --> JOIN
  JOIN --> PREP[Prepare plan approval]
  PREP --> APPROVAL[Plan approval interrupt]
  APPROVAL -->|Approved or approval disabled| Q[Query generator]
  APPROVAL -->|Rejected or cancelled| F[Finalizer]
  Q -->|Queries available| SOURCE[Source processor]
  Q -->|No usable query| COVERAGE[Coverage evaluator]
  SOURCE --> EXTRACT[Evidence extractor]
  EXTRACT --> ANALYSIS[Evidence intelligence]
  ANALYSIS --> COVERAGE
  COVERAGE -->|Gap and allowance| Q
  COVERAGE -->|Evidence and bounded stop| SYN[Synthesis]
  COVERAGE -->|No evidence| F
  SYN --> CRITIC[Critic]
  CRITIC -->|Revision and allowance| REWRITE[Reserve shared rewrite]
  CRITIC -->|Otherwise| CITE[Citation checker]
  CITE -->|Repair and allowance| REWRITE
  REWRITE --> SYN
  CITE -->|Audited or exhausted| F
  F --> DELIVERY[Persist reports and inspection exports]
```

Synthesis failures route to citation checking if a draft exists, otherwise to
finalization. Non-running/error/cancelled states also route to finalization.
The diagram summarizes healthy paths; error routes are enforced in
`src/evidenceforge/graph/research.py`. Finalization preserves only audited claims
and may return completed, partial, insufficient_evidence, failed or cancelled.

## Storage and access

```mermaid
flowchart LR
  ENTRY[CLI or local workbench] --> APP[Application services]
  APP --> GRAPH[LangGraph state and reducers]
  GRAPH <--> CHECKPOINT[SQLite checkpoint and run registration]
  APP <--> DOC[Scoped document and prior-report repositories]
  GRAPH --> LEDGER[Durable call reservations and receipts]
  GRAPH --> SNAPSHOT[Immutable source snapshots and exact offsets]
  GRAPH --> EXPORT[Markdown and JSON exports]
  MODEL[Fixture or Gemini adapter] <--> GRAPH
  ACQUIRE[Explicit energy or Tavily acquisition command] --> RETRIEVAL[RetrievalService]
  APP --> RETRIEVAL
  RETRIEVAL --> API[Explicit Tavily and GB energy endpoints]
  RETRIEVAL --> DOC
  RETRIEVAL --> LEDGER
  RETRIEVAL --> SNAPSHOT
```

The full research graph can retrieve explicitly enabled Tavily web/API sources and
scoped documents together. Default runs use synthetic retrieval or selected documents;
standalone acquisition commands also remain available. Source options survive checkpoint
reconnect, and factory-owned HTTP clients close after success, pause or failure.

Coverage, synthesis and criticism receive a literal deduplicated working set plus
member IDs, source/acquisition provenance and exact locators. Original passage records
remain immutable; only complete exact-copy quotes gain additional cited occurrences.
Containment never licenses quoting missing text. Distinct wording/question links are
preserved; copied text is not an independent vote. Prior reports are context/navigation,
never admitted
as fresh evidence. Owner IDs are storage boundaries and must match requests,
documents, checkpoints and exports; they do not authenticate users.

## Where behavior lives

| Responsibility | Current implementation |
|---|---|
| Research routing | `src/evidenceforge/graph/research.py` |
| State/contracts | `src/evidenceforge/graph/state.py`, `schemas.py` |
| Application lifecycle | `src/evidenceforge/services/research.py` |
| Planning and context | `nodes/planner.py`, `nodes/context.py`, `nodes/queries.py` |
| Retrieval and evidence | `nodes/sources.py`, `nodes/extraction.py`, `retrieval/` |
| Coverage/quality | `nodes/quality.py`, `reporting.py` |
| Evidence graph/comparisons | `evidence/`, `nodes/intelligence.py` |
| Call/restart persistence | `storage/checkpoints.py`, `storage/calls.py`, `storage/model_calls.py` |
| UI and worker facade | `ui.py`, `workbench.py`, `ui_launcher.py` |
| Gemini reasoning | `models/gemini.py` |
| GB energy acquisition | `retrieval/carbon_intensity.py`, `energy_demo.py` |
| Evaluation | `evaluation.py`, `evaluation_paid.py`, `evaluation_extension.py` |

Rows with short filenames are relative to `src/evidenceforge/`.
The claim graph is a projection of authoritative records, not a second mutable
truth store. Ranking, lexical admission and explicit numeric comparisons are
heuristics; successful citation checks do not independently establish source truth.
