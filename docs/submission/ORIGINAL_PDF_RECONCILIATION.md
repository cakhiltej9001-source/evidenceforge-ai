# Original PDF reconciliation

The initial snapshot audit is preserved below. The 5 October implementation update
and [passing verification](../ASSIGNMENT_FIXES_2026-10-05.md) supersede its runtime
gap statuses.

Reviewed 4 October 2026, Asia/Calcutta, against source revision
`93b320d65d87dd449905ddc65d91315ef0bf3303`.

## Source and scope

The user supplied `C:/Users/AKHILTEJ/Downloads/AI Research Agent(1).pdf`.
Title: **AI Research Agent: A LangGraph Multi-Agent System for Autonomous Research**.
23 pages, 1,078,834 bytes. SHA-256:
`51ee3f8022090e5806cbd51ac48fc77c4bbde4bbf0d5fc8f82ccd08e8722840c`.

All 23 pages were read. Pages were rendered for visual review; the image-only
pipeline on page 5 and the report/production tables were inspected directly.
Text, source manifest and review renders are retained under ignored
`.evidenceforge/requirements/original-assignment/`. The supplied PDF is unmodified.

The document is an implementation tutorial with production guidance. It has no
scored judging rubric, submission deadline, competition submission format,
benchmark size, human-review requirement or required hosting platform. Its content
is the reference for this reconciliation; document examples do not independently
authorize provider calls, credential searches, uploads or deployment.

The original-file/page-mapping gate is now closed. Overall baseline compliance is
**partial**, because the full live research path and report presentation still
have concrete gaps. The 350 passing source tests establish engineering behavior,
not completion of every PDF feature.

## Baseline traceability

B/P identifiers are the project's mapping IDs, not labels printed in the PDF.
Paths below are relative to `src/evidenceforge/`; tests are under `tests/`.
Implemented means the specified workflow mechanic exists, subject to its stated
limits. Partial identifies a specific feature difference.

| ID | PDF pages | Reference behavior | Repository evidence | Result |
|---|---|---|---|---|
| B01 | 2, 6, 8-9 | Focused research subquestions | `nodes/planner.py`, `schemas.py`; planning tests | Implemented with structured IDs/criteria; quality remains model-dependent |
| B02 | 2, 5-6, 10 | Web, supplied documents and API/MCP paths in the research pipeline | `retrieval/tavily.py`, `documents.py`, `carbon_intensity.py`, `contracts.py`, `services/research.py` | Partial: documents/fixtures feed the full graph; Tavily and live NESO acquisition are separate commands; ResearchService rejects live retrieval adapters |
| B03 | 5, 8-9 | Manager initializes Planner and Context Manager before querying | `graph/research.py`, `nodes/manager.py`, `context.py`; parallel planning tests | Implemented fan-out and explicit all-predecessor join |
| B04 | 6, 9-10 | Query Generator produces source-specific queries | `nodes/queries.py`; planning query tests | Implemented for configured source types and coverage gaps |
| B05 | 6, 10-11 | Relevant passages, scoring, cross-source deduplication and provenance | `nodes/extraction.py`, `sources.py`, `evidence/ranking.py`; retrieval/analysis tests | Partial: exact spans, lexical threshold and same-record merges exist; copied source families/hashes affect analysis, but cross-source overlapping passages are not merged into one retained chunk |
| B06 | 7-8 | Shared TypedDict state with deliberate merge semantics | `graph/state.py`, `reducers.py`; state tests | Implemented; keyed replay-safe merges replace the tutorial's simple append example |
| B07 | 11-12, 15 | Missing coverage produces targeted follow-up queries | `nodes/quality.py`, `graph/research.py`; second-pass research test and live repair record | Implemented; fixture heuristic or Gemini criteria assessment |
| B08 | 12, 20 | Bounded iteration stop with incomplete-coverage disclosure | `nodes/quality.py`, `reporting.py`; pass-limit tests | Implemented; additional call/search/time/byte limits and honest partial/insufficient states |
| B09 | 13 | Markdown Summary, Key Findings, Sources; 2-3 paragraph summary and per-source evidence chunks | `reporting.py`, `exports.py`; report/research tests | Partial: required headings and cited quoted findings exist; summary is bullets, and Markdown Sources lacks its own per-source chunk list; full evidence is in inspection/state exports |
| B10 | 13-16 | Critic checks coherence/grounding/completeness and requests a rewrite | `nodes/quality.py`, `graph/research.py`; critic/repair tests | Implemented structured review and bounded revision; model verdict is fallible |
| B11 | 6, 14 | Every delivered factual claim traces to retained evidence and source | `nodes/quality.py`, `evidence/projection.py`, `reporting.py`; citation tests | Implemented conservatively for registered exact quotations; arbitrary paraphrase entailment and independent source truth are not established |
| B12 | 14-16, 22-23 | Register/connect/compile StateGraph and conditional routes | `graph/research.py`, `graph/builder.py`; graph/research tests | Implemented and executed; approval/analysis/finalization extend the tutorial graph |
| B13 | 16, 23 | SQLite checkpoints with thread IDs and persistent context | `storage/checkpoints.py`, `local_context.py`, `services/research.py`; persistence tests and Docker reconnect | Implemented local SQLite state and scoped prior-report context; production PostgreSQL is not configured |

## Incremental production guidance

Section 9 says these concerns can be implemented incrementally (page 19). They
are listed separately from the baseline; passing the local foundation is not a
claim of full production readiness.

| ID | PDF pages | Guidance | Current implementation and gap |
|---|---|---|---|
| P01 | 3-4 | Environment secrets and ignored dotenv | Implemented with namespaced settings, redaction and Git/Docker exclusions |
| P02 | 19 | Small-model classification of valid, gibberish, nonresearch, manipulation and vague requests | Partial: deterministic schema/known-vague checks exist; no semantic classifier or complete coverage of the PDF's five example categories |
| P03 | 19-20 | Prompt/tool/routing/latency/token observability through LangSmith or LangFuse | Partial: local events, node timing and known usage; opt-in allowlisted LangSmith counters exist. Full prompt/tool-payload tracing is deliberately disabled; remote delivery is unverified |
| P04 | 21 | Structured tool failures plus ordered fallback to another search provider after failure/empty results | Partial: typed failures and bounded same-provider retrieval retries exist; no ordered multi-provider search chain. Manually selecting a Gemini model does not satisfy this search fallback feature |
| P05 | 21 | Relevance threshold, size limit, lowest-score eviction and stored prior reports | Partial: threshold/count/byte caps and prior-report context exist. New passages are rejected at capacity; lower-scoring admitted passages are not evicted |
| P06 | 22 | Restrict tools by planning/retrieval/evaluation/synthesis phase | Implemented with injected read-only adapters and structured model ports; models receive no arbitrary execution/write tools |

## Important interpretations

- **API/MCP:** pages 2 and 10 describe APIs or MCP servers; page 10 calls this an
  extensibility point. The PDF does not require a particular live MCP server.
  A real NESO API adapter plus the retrieval contract supports extension, but a
  separate acquisition command does not fulfill same-pipeline integration.
- **Search provider:** Tavily is the recommended default; page 4 explicitly
  permits alternatives. Live web research remains a baseline feature. A Tavily
  key is an access dependency for the current adapter, not a uniquely mandated
  brand of search service.
- **Dependencies:** the package uses LangGraph, dotenv-backed settings, pypdf,
  python-docx and SQLite checkpoints. Gemini/Tavily use direct HTTPX REST ports
  instead of the tutorial's LangChain provider wrapper/Tavily SDK. This is an
  implementation difference, not evidence that those SDKs were installed.
- **Manager/model:** page 8 describes a higher-capability manager. The current
  manager is deterministic; Gemini handles planning/quality. The user-authorized
  lighter-model fallback remains configured; no new paid call ran for this audit.
- **State:** page 8 explicitly permits extending the minimal example. Typed claim,
  source and receipt records plus replay-safe reducers are intentional extensions.
- **Diagram and walkthrough:** page 5 shows parallel initialization; prose on
  pages 8-9 establishes context before queries. The implementation waits for both
  branches. Page 17 labels query creation as a Planner step once and pages 17-18
  duplicate walkthrough steps; the page 6 role definitions govern the mapping.
- **Grounding:** the PDF's self-critique/hallucination claims are tutorial claims,
  not measured results for this project. Exact retained quotation checks prove
  text support, not source accuracy.
- **Additional project goals:** Docker/Render deployment, Streamlit, a 20-case
  benchmark, an independent human review and a demo duration originate from the
  project plan. The PDF does not specify them as grading requirements. Existing
  authorized engineering work and evaluation qualifications remain recorded.

## Follow-up order

| Priority | Work | Phases affected | Verification needed |
|---|---|---|---|
| 1 | Explicitly integrate live web/document/external acquisition with full research and reconnect | 3, 8, 10 | Mixed-source graph, durable search receipts, failures/cancellation/approval/reconnect; authorized live access |
| 2 | Add the specified evidence-backed summary paragraphs and per-source chunk list | 4, 8, 11 | Every rendered factual sentence remains audited; paragraphs never padded with unsupported facts |
| 3 | Merge overlapping cross-source passages while retaining all source/acquisition provenance | 3, 6 | Deduplication cannot erase independent evidence, change exact locators or inflate agreement |
| 4 | Implement production semantic input review, configured ordered search fallback and evidence eviction | 7 | PDF category decisions; per-provider reservations/receipts; preserved cited evidence and bounded memory |
| 5 | Verify an explicitly configured tracing policy and persistent host when requested | 7, 10 | Actual delivery, account access and runtime/storage/security checks |

The read/reconciliation task is complete. These are documented implementation
gaps, not passing results or an instructor's sign-off. The original 26/30 and
additional 28/40 Gemini ledgers are unchanged. No external provider call, credential
search, PDF edit or hosting resource creation was needed for this audit.

## Implementation update — 5 October 2026

The table above preserves the original audit against `93b320d`. The user then
instructed Codex to continue the pending work. B02/B09 and the conservative literal
part of B05 now have runtime implementations:

- **B02:** opt-in `--live-web` / `--energy-api` and UI controls combine Tavily,
  GB half-hour API data and scoped documents in the full research graph. Source
  choices persist through approval, editing and reconnect. Missing search keys fail
  before planning; completed reconnect reuses durable receipts; HTTP clients close
  on success, pause, configuration mismatch and editing failure.
- **B09:** Summary renders 2–3 paragraphs of audited quotes when enough supported
  claims exist. It discloses a short summary if fewer exist. Each cited source lists
  retained evidence chunks and exact offsets/page/paragraph locations.
- **B05:** coverage/synthesis/critic receive a deduplicated working set for literal
  copies and fully contained passages whose question associations are represented.
  Original evidence/source/acquisition/snapshot/locator records remain retained.
  Exact-copy occurrences can add citations only when the complete claim quote is
  present and the question links match; every occurrence still passes citation audit.
  Different wording, nonidentical partial overlaps, qualifiers, owners and uncovered
  question associations remain separate. Semantic equivalence is not inferred.

These changes address the tutorial mechanics without claiming source truth or
independent corroboration. The current [requirements checklist](REQUIREMENTS.md)
and [implementation record](../ASSIGNMENT_FIXES_2026-10-05.md) describe verification.
Actual Tavily access, persistent hosted verification, independent human review and
P02–P05 incremental production differences remain qualified. This update made no
new Gemini/search calls and did not modify the original PDF or frozen benchmark.
