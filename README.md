# EvidenceForge AI

A local research workbench that plans questions, retains source passages, follows
coverage gaps and produces reports with inspectable claim support. Python,
LangGraph, SQLite and an optional Streamlit UI provide the workflow.

**Status:** local workflows, public energy acquisition and remote Docker CI are verified.
The source is in a private GitHub repository; Phase 11 submission materials are prepared.
All 20 Gemini one-shot responses are available, and the repaired workflow completed its
model stages. Research-quality validation, persistent hosting, live Tavily access and
the remaining production guidance need further verification. Explicit mixed-source
research, paragraph summaries and conservative passage deduplication are implemented.
The original 23-page PDF has been reviewed in the [reconciliation](docs/submission/ORIGINAL_PDF_RECONCILIATION.md).
Synthetic demonstrations show workflow behavior, not independently verified facts.

## Start here — Windows PowerShell

Use Python 3.12 and uv. The dependency lock is retained in `uv.lock`.

```powershell
cd "C:\Users\AKHILTEJ\Documents\ChatGPT\AI Research agent"
uv sync --locked --extra ui
uv run --locked evidenceforge-research "Compare solar and wind electricity output." --demo second-pass --offline
uv run --locked --extra ui evidenceforge-ui
```

Open http://127.0.0.1:8501. Choose **offline** reasoning for the synthetic demo.
The UI supports question entry, plan editing/approval, progress, cancellation,
checkpoint reconnect, document upload, finding inspection and report downloads.
Scope names isolate local storage; they are not login credentials.

`--offline` forces fixture reasoning even when a private `.env` configures Gemini.
The standalone planning/retrieval CLIs require fixture configuration; the research
CLI and dedicated energy command have separate controls. See [setup](docs/submission/SETUP.md).

## Four-minute demonstration

Prepare an inspectable replay with no external provider calls:

```powershell
uv run --locked python scripts/prepare_demo.py
uv run --locked python -m http.server 8503 --bind 127.0.0.1 --directory .evidenceforge/demo/phase11
```

Open http://127.0.0.1:8503. Four executed synthetic scenarios demonstrate a second
retrieval pass, a numeric dispute, an unsupported draft repaired by the citation
checker, and a partial answer at the pass limit. Click a finding for its exact
passage, locator and selected support graph. The initial bad draft is deliberately
scripted and labeled; final reports contain only retained supported quotations.
Stop the replay server with Ctrl+C. It serves only the generated demo directory.

[Demo script](docs/submission/DEMO.md) · [Architecture](docs/submission/ARCHITECTURE.md)
· [Requirements checklist](docs/submission/REQUIREMENTS.md)

## Features and boundaries

| Feature | Implemented behavior |
|---|---|
| Planning | Structured questions/criteria; concurrent planner/context branches join once |
| Evidence | Bounded retrieval, snapshots, exact locators; literal working-set deduplication with all original provenance retained |
| Coverage | Follow-up questions with pass/search/model/time/byte limits |
| Reports | 2–3 supported summary paragraphs where evidence permits; findings, per-source chunks, disagreements and disclosed gaps |
| Citation checks | Exact quoted text and retained snapshot checks; bounded repair/omission |
| Analysis | Heuristic ranking, source families and supported scoped numeric comparisons |
| Persistence | Owner-scoped SQLite checkpoints and durable model/search receipts |
| Documents | TXT/PDF/DOCX ingestion, page/paragraph/table locations; OCR unavailable |
| Reasoning | Offline fixtures by default; configured Gemini structured stages |
| Live sources | Explicit Tavily and read-only NESO GB half-hour shares, combined with selected documents in full research |

Full research can combine explicitly selected Tavily web search, the GB energy API,
and supplied documents. The CLI uses `--live-web` and `--energy-api`; matching UI
checkboxes are off by default. These choices survive approval/editing/reconnect.
Missing search credentials fail before planning. `--offline` excludes live sources.
Exact citation matches establish retained-text support, not source truth. See
[limitations](docs/submission/LIMITATIONS.md).

## Local documents and restart

```powershell
uv run --locked evidenceforge-ingest tests/fixtures/documents/energy.txt --owner demo
uv run --locked evidenceforge-research "Compare solar and wind electricity output." --owner demo --document DOCUMENT_ID --offline
uv run --locked evidenceforge-research "Compare solar and wind electricity output." --demo second-pass --require-approval --offline
uv run --locked evidenceforge-research --resume THREAD_ID --approve-plan 1 --offline
```

Replace `DOCUMENT_ID` and `THREAD_ID` with the preceding command outputs. Keep the
same owner/data directory on reconnect. Plan edits create a new version requiring
renewed approval. Supported current checkpoints use graph version 8; earlier graph
versions and historical paid runs without receipts cannot silently migrate.

## Optional source and Gemini access

```powershell
uv run --locked evidenceforge-energy
uv run --locked evidenceforge-energy --live
```

The first is synthetic. The second performs one public NESO GET, needs no API key
and makes no Gemini calls. It retains evidence and state rather than generating a
research report. Its percentages describe Great Britain's returned half-hour mix,
including imports; they do not measure global or annual output in MWh.

To configure Gemini, save the following privately in `.env`:

```dotenv
EVIDENCEFORGE_MODEL_PROVIDER=gemini
EVIDENCEFORGE_MODEL_ID=gemini-3.5-flash-lite
EVIDENCEFORGE_MODEL_API_KEY=YOUR_PRIVATE_KEY
```

This is the model used in the recorded verification, not a claim about the newest
available model or current availability. Gemini sends the question and relevant
passages/context to Google. Select its UI mode or omit `--offline` from research
commands using documents, an explicit demo or explicitly enabled live sources. Configure
call/token limits before paid
use. Completed responses can replay from durable receipts; failed/unconfirmed calls
are not automatically retried. Dollar ceilings require a verified pricing policy.

`.env`, `.evidenceforge`, documents, databases and traces are ignored by Git.
Never include local private data in a submission or Docker build context.

## Measured evaluation

[Results and interpretation](docs/submission/EVALUATION.md) separates synthetic
workflow scores from provider outcomes. All 40 fixture variants ran. Full-agent
aspect coverage was 1.0 in both partitions; one-pass coverage was 0.5 development
and 0.6667 held out. These are exact-string measures on draft synthetic labels.

The original Gemini evaluation reserved 26/30 calls. The separately authorized
extension and repair checks used 28/40 additional calls, recovering the eight missing
responses for 20/20 usable one-shot cases. A fresh repaired workflow made nine
successful calls and returned two cited claims, partial at the three-pass limit.
All 20 annotations received an [AI review](docs/evaluation/AI_REVIEW.md); the draft
labels remain qualified for synthetic workflow checks. Research-quality validation
is still open. [Extension results](docs/evaluation/EXTENSION_REPORT.md) retain every
failure and disclose unknown usage/cost.

## Development and deployment

```powershell
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv build
```

Tests use synthetic credentials and block ordinary network connections. Optional
UI checks need `--extra ui` in the installation. [Phase 11](docs/PHASE11.md) records
final verification; [progress](docs/PROGRESS.md) preserves earlier executed results.

Docker, localhost Compose and a private Render template are prepared. The
[private repository](https://github.com/cakhiltej9001-source/evidenceforge-ai) has a
[successful CI run](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37253453020)
covering **362 tests**, strict typing/lint/format, package build and Render schema.
Docker build, UID 10001, research/reconnect, fresh-volume synthetic backup/restore
under 512 MB and half-CPU limits, and UI health also passed. This run verified
source `36d1e44a414bbc9ced7a74fa151b30faffd53593`; source pushes repeat the checks.
Persistent hosted storage/access remains unverified. No Render resources or public
endpoint have been created. [Deployment details](docs/PHASE10.md).

## Submission materials

- [Setup guide](docs/submission/SETUP.md)
- [Architecture and data boundaries](docs/submission/ARCHITECTURE.md)
- [3–5 minute demo](docs/submission/DEMO.md)
- [Requirement traceability](docs/submission/REQUIREMENTS.md)
- [Evaluation table](docs/submission/EVALUATION.md)
- [Limitations and open gates](docs/submission/LIMITATIONS.md)

The original 23-page PDF is now supplied and reviewed. Its graph/source/report
requirements are mapped in the [original-PDF reconciliation](docs/submission/ORIGINAL_PDF_RECONCILIATION.md).
Live web/API retrieval in the full research pipeline and the specified summary/source
presentation remain incomplete. The PDF contains no grading rubric, deadline or
hosting mandate; full assignment acceptance is not claimed.


## Quality-input checkpoint compatibility

New runs register quality-input version 2 for literal working-set deduplication and
multi-claim summary selection. Existing graph-version-8 profiles without that marker
restore version 1: original evidence ordering, claim/summary selection and empty-field
serialization are preserved for paid receipt hashes. Completed reconnect still makes
no new provider call. Older runs retain their historical findings; start a new run to
use the updated quality behavior. Graph versions predating 8 and paid runs without
durable receipts retain their existing incompatibility checks.

[Original assignment fixes and verification](docs/ASSIGNMENT_FIXES_2026-10-05.md).
