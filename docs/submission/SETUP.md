# Setup and reproduction

## Requirements and install

The tested interpreter family is Python 3.12. `pyproject.toml` permits 3.12 through
3.14; the lock selects exact dependencies for supported platforms. Use uv and the
lock for reproducible installation. The UI is an optional extra.

```powershell
cd "C:\Users\AKHILTEJ\Documents\ChatGPT\AI Research agent"
uv sync --locked --extra ui
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv run --locked evidenceforge-check
```

The copy step preserves an existing private `.env`. Configuration checks print
sanitized settings, not key values. A new copy defaults to fixtures and needs no
credentials. If existing dotenv values are malformed, fix them before using the
CLI. Environment variables override dotenv; do not publish private configuration.

## Offline report, UI and replay

```powershell
uv run --locked evidenceforge-research "Compare solar and wind electricity output." --demo second-pass --offline
uv run --locked --extra ui evidenceforge-ui
```

Open http://127.0.0.1:8501. Use offline reasoning, choose the second-pass fixture,
review/edit the proposed plan and approve its current version. The UI shows the
thread identifier, timeline, coverage, usage and report. Use the finding selector
for passages/locators; Markdown and allowlisted JSON downloads are available.

For a captured demo that also includes repair and partial results:

```powershell
uv run --locked python scripts/prepare_demo.py
uv run --locked python -m http.server 8503 --bind 127.0.0.1 --directory .evidenceforge/demo/phase11
```

Open http://127.0.0.1:8503; stop with Ctrl+C. This replay serves only generated
synthetic data. The preparation script asserts observed workflow outcomes and
writes `manifest.json`, an HTML index and service-produced reports/state/graphs.
The audit repair uses a clearly labeled deliberately incorrect first draft.
These demonstrations make no provider requests, including when `.env` uses Gemini.

## Documents and claim inspection

```powershell
uv run --locked evidenceforge-ingest tests/fixtures/documents/energy.txt --owner demo
uv run --locked evidenceforge-research "Compare solar and wind electricity output." --owner demo --document DOCUMENT_ID --offline
uv run --locked evidenceforge-inspect "ABSOLUTE_STATE_JSON_PATH" --owner demo --claim CLAIM_ID
```

Use the ingestion output's document ID and the saved report directory's state path.
Claim IDs are in `inspection.md`/`state.json`. The owner must match. Ingestion stores
a content version; it does not grant an authenticated identity. PDF/DOCX/TXT input
is bounded; scanned/textless PDFs disclose unavailable OCR.

## Approval, edit and process restart

```powershell
uv run --locked evidenceforge-research "Compare solar and wind electricity output." --demo second-pass --require-approval --offline
uv run --locked evidenceforge-research --resume THREAD_ID --approve-plan 1 --offline
uv run --locked evidenceforge-research --resume THREAD_ID --offline
```

Use the returned thread ID and same owner/data directory. Completed reconnect does
not run new provider work. An edited plan uses `--edit-plan PLAN_JSON --plan-version
CURRENT_VERSION`, increments the plan version and requires a new approval.
`--data-dir` must also be supplied on reconnect if overridden at creation.
`--cancel THREAD_ID` requests cooperative cancellation; resume a paused run to
finalize it. Create a fresh service/model for every new paid run.

## Optional external access

| Workflow | Requirements | What leaves the machine |
|---|---|---|
| Offline examples/replay | None | No provider request |
| Gemini document/explicit synthetic report | Configured model ID/key; approved call/token limits | Question, relevant passages and scoped prior context |
| NESO acquisition (`evidenceforge-energy --live`) | Public HTTPS access, no key | One fixed GET, no prompt or document payload |
| Tavily acquisition (`evidenceforge-retrieve --live`) | Tavily key and fixture planning configuration | Generated search query |
| Full mixed-source research (`--live-web`, `--energy-api`) | Explicit flags; Tavily key for web; chosen reasoning configuration | Search queries to Tavily; fixed GET to NESO; selected evidence/context to Google only with Gemini |

`evidenceforge-energy` without `--live` is synthetic. It retains source evidence
and state and does not generate a report. Gemini reasoning alone does not enable
web search; explicit live-source choices control acquisition separately. Recorded
historical fallback use does not establish
the model's current availability. Failed/unconfirmed paid calls are not automatically
retried; historical paid checkpoints without receipts cannot migrate.

## Explicit mixed-source research

Privately configure `EVIDENCEFORGE_TAVILY_API_KEY` in the current project's `.env`
to enable web search. Ingest an authorized document and use its returned ID:

```powershell
uv run --locked evidenceforge-research "Compare solar and wind electricity output, distinguishing GB half-hour shares from annual output." --owner demo --document DOCUMENT_ID --live-web --energy-api --require-approval
uv run --locked evidenceforge-research --resume THREAD_ID --owner demo --approve-plan 1
uv run --locked evidenceforge-research --resume THREAD_ID --owner demo
```

Both live flags are optional. Configure the reasoning provider separately; omitting
`--offline` follows the current private model settings and can consume Gemini calls.
Live source flags cannot be combined with `--offline` or `--demo`. On reconnect the
saved source choices, owner and document IDs are restored. Completed reconnect
makes no new search request. Missing Tavily credentials fail before planning.

In the UI, use **Search live web with Tavily** and/or **Include GB half-hour energy
API**, select any document IDs, and create/review the plan. The energy API describes
GB shares in one half-hour, not annual/global/absolute output. Selecting it does not
promise that it can answer every requested comparison. The synthetic scenario is
used only when no live source or document is selected.

Summary paragraphs contain audited quotations and shorten with disclosure if fewer
than two supported claims exist. Sources list cited evidence chunks with exact
locators. Literal copies/contained passages are grouped for model input; all original
records remain retained. Distinct facts, qualifiers and uncovered question links are
preserved. Grouping does not establish independent corroboration.

The mixed-source path is verified with mocked HTTP. Actual Tavily acquisition/full
pipeline/recovery passed on 5 October; a live Wikipedia fallback passed on 6 October
after a simulated primary failure. These checks do not establish semantic source truth.

## Files and storage

Local data defaults to `.evidenceforge` (ignored). Keep the complete data root for
checkpoints, receipts, documents, reports and context memory. Report directories
contain Markdown, allowlisted JSON, state, graph, audit, inspection and usage data.
Exports may contain selected document passages; review before sharing.

Run the local cold-reconnect check:

```powershell
uv run --locked python scripts/deployment_smoke.py --data-dir .evidenceforge/verification/my-smoke
uv run --locked python scripts/deployment_smoke.py --data-dir .evidenceforge/verification/my-smoke --reconnect
```

For Docker, persistent storage, private Render setup and verification dependencies,
see [Phase 10](../PHASE10.md). The image places Caddy in front of loopback-only
Streamlit; set `CADDY_AUTH_REQUIRED=true`, `CADDY_AUTH_USERNAME` and a bcrypt
`CADDY_AUTH_PASSWORD_HASH` to protect all browser routes while keeping the health
path available. The future Render template additionally requires
`EVIDENCEFORGE_AUTH_REQUIRED=true` and a PBKDF2
`EVIDENCEFORGE_AUTH_PASSWORD_HASH` for in-app login; hosted checks fail closed without
it. Local Docker prerequisites are unmet on the current host; remote Docker CI
has passed in the private repository. Persistent Render
deployment is deferred by the user’s local durable-storage choice. No public endpoint
is configured. Keep the entire `.evidenceforge` directory for local backups; restarting
the UI preserves saved research.

## Final checks

```powershell
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv build
```

Offline tests block network access and use fabricated secrets. Type/lint/format
checks are engineering checks, not research-quality measurements. See
[Phase 11 verification](../PHASE11.md) for the executed results.


## Quality-input checkpoint compatibility

New runs register quality-input version 2 for literal working-set deduplication and
multi-claim summary selection. Existing graph-version-8 profiles without that marker
restore version 1: original evidence ordering, claim/summary selection and empty-field
serialization are preserved for paid receipt hashes. Completed reconnect still makes
no new provider call. Older runs retain their historical findings; start a new run to
use the updated quality behavior. Graph versions predating 8 and paid runs without
durable receipts retain their existing incompatibility checks.
