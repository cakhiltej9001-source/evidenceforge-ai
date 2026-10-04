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

`evidenceforge-energy` without `--live` is synthetic. It retains source evidence
and state and does not generate a report. Gemini mode does not enable external
web search in the research UI. Recorded historical fallback use does not establish
the model's current availability. Failed/unconfirmed paid calls are not automatically
retried; historical paid checkpoints without receipts cannot migrate.

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
see [Phase 10](../PHASE10.md). Local Docker prerequisites are unmet on the current
host; remote Docker CI has passed in the private repository. Persistent Render
deployment remains unverified. No public endpoint is configured.

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
