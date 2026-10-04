# EvidenceForge AI

A local research workbench that plans questions, retains source passages, follows
coverage gaps and produces reports with inspectable claim support. Python,
LangGraph, SQLite and an optional Streamlit UI provide the workflow.

**Status:** local workflows and source acquisition are verified. Submission materials
are prepared in Phase 11. Phase 9 human annotation/provider comparisons, hosted
Docker/deployment checks, and original assignment PDF/rubric reconciliation remain open.
The synthetic demonstrations show workflow behavior, not independently verified facts.

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
| Evidence | Bounded retrieval, snapshots, exact locators, deduplication and provenance |
| Coverage | Follow-up questions with pass/search/model/time/byte limits |
| Reports | Summary, findings, sources, disagreements and disclosed gaps |
| Citation checks | Exact quoted text and retained snapshot checks; bounded repair/omission |
| Analysis | Heuristic ranking, source families and supported scoped numeric comparisons |
| Persistence | Owner-scoped SQLite checkpoints and durable model/search receipts |
| Documents | TXT/PDF/DOCX ingestion, page/paragraph/table locations; OCR unavailable |
| Reasoning | Offline fixtures by default; configured Gemini structured stages |
| Specialized API | Explicit read-only NESO half-hour GB generation mix acquisition |

The full research service uses local documents or synthetic retrieval. The NESO
and Tavily adapters have explicit acquisition commands; they do not enable general
live web research in the UI. Exact citation matches establish retained-text support,
not source truth. See [limitations](docs/submission/LIMITATIONS.md).

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
commands using documents/an explicit demo. Configure call/token limits before paid
use. Completed responses can replay from durable receipts; failed/unconfirmed calls
are not automatically retried. Dollar ceilings require a verified pricing policy.

`.env`, `.evidenceforge`, documents, databases and traces are ignored by Git.
Never include local private data in a submission or Docker build context.

## Measured evaluation

[Results and interpretation](docs/submission/EVALUATION.md) separates synthetic
workflow scores from provider outcomes. All 40 fixture variants ran. Full-agent
aspect coverage was 1.0 in both partitions; one-pass coverage was 0.5 development
and 0.6667 held out. These are exact-string measures on draft synthetic labels.

The Gemini evaluation reserved 26/30 calls and yielded 12 usable one-shot responses
from 20 cases. Both bounded full-agent probes ended partial/failed. A successful
matched provider quality comparison and independent human label review remain
open. Token/cost/latency fields are reported as unknown where not verified.

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

Docker, localhost Compose, a private Render template and CI are prepared. Official
Render schema validation, local restart and synthetic backup/restore passed.
Container execution and hosted runtime remain unverified. No hosting resources or
public deployment have been created. [Deployment details](docs/PHASE10.md).

## Submission materials

- [Setup guide](docs/submission/SETUP.md)
- [Architecture and data boundaries](docs/submission/ARCHITECTURE.md)
- [3–5 minute demo](docs/submission/DEMO.md)
- [Requirement traceability](docs/submission/REQUIREMENTS.md)
- [Evaluation table](docs/submission/EVALUATION.md)
- [Limitations and open gates](docs/submission/LIMITATIONS.md)

The original assignment PDF and judging rubric have not been supplied. Requirement
mapping follows the preserved handoff and cannot establish assignment compliance.
