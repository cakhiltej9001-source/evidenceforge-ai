# Phase 8 — local interaction and exports

## Scope

Streamlit uses ResearchService with offline fixture or configured Gemini reasoning. It supports
synthetic demos and scoped local documents. Gemini sends the selected request, evidence and
context to Google using the private configured key. Tavily/live web retrieval is not enabled.
A separate FastAPI server is not needed for this local application.

## Run

In PowerShell:

```powershell
cd "C:\Users\AKHILTEJ\Documents\ChatGPT\AI Research agent"
uv sync --locked --extra ui
uv run --locked --extra ui evidenceforge-ui
```

Open http://127.0.0.1:8501. The launcher binds localhost, disables Streamlit usage telemetry,
and limits uploads to 4 MB. This is a single-machine demonstration, not a deployed multiuser
application. Local scope labels separate stored records; they do not authenticate people.

1. Select a local scope. Import PDF/DOCX/TXT evidence or choose a synthetic scenario.
2. Enter a specific question, choose **Offline** or **Gemini (configured)**, and select **Create plan**.
3. Review the generated questions and criteria. Edit/add/remove rows when needed and save.
   Saving creates a new plan version; approve or reject that version to proceed.
4. Follow the sanitized timeline, coverage/gaps and budget/usage panels. **Cancel research** requests cooperative cancellation.
5. Inspect a finding's passages, locators, sources, links, audit results, rankings and disputes.
6. Download Markdown or the JSON report. Downloads include selected private document text
   when local documents were used; review them before sharing.
7. Use **Reconnect / Open saved run** after reopening the page. Stored checkpoints retain
   approved/rejected decisions. A worker already executing in this server continues when
   the page closes; stopping the server stops its workers. Resume interrupted work
   through the saved thread once no writer is active.

## Approval and persistence

A dedicated side-effect-free LangGraph interrupt follows the planner/context join and
precedes query generation. A small preparation node records awaiting_approval so reconnect
can display the correct status. It makes no model or retrieval calls. The interrupt node
may restart on resume; no calls or writes occur before interrupt(). Decisions require a
strict boolean and current plan version. Wrong scope, stale decisions and decisions for
finalized threads are rejected. Rejection finalizes as cancelled without retrieving.

Plan editing validates focused/distinct questions, criteria, importance, JSON size and the
immutable subquestion budget. It is allowed only before queries/retrieval. The service
assigns question IDs, increments the plan version, updates the checkpoint under the writer
lock and re-enters the dedicated approval node. Planning/model calls are not repeated. A
stale edit or approval is rejected, and the new plan cannot proceed without renewed review.

Graph version is now 8. New workflows use the new graph. Existing Phase 7 registrations
are retained; resume configuration mismatch is reported rather than silently migrating
workflow positions. Start a fresh Phase 8 run to use approval.

The UI runs operations in a bounded background executor so refresh/cancel remain usable.
It permits one UI operation at a time. SQLite single-writer locks also protect direct CLI
concurrency. Browser progress and the stable-ID timeline are derived from validated, owner-scoped checkpoints.
Timeline messages are allowlisted labels, not raw event/model/document text. It
never streams raw state/context/logs to the page. Deliberate evidence inspection and exports
include the selected passages. Polling reads do not invoke the graph or make provider calls.

## CLI

```powershell
uv run --locked evidenceforge-research "Compare solar and wind electricity output." --offline --demo second-pass --require-approval
# Use the printed thread ID and plan version:
uv run --locked evidenceforge-research --offline --resume THREAD_ID --approve-plan 1
# To edit, create a PlanDraft JSON with a questions array (question, acceptance_criteria, importance):
uv run --locked evidenceforge-research --offline --resume THREAD_ID --edit-plan plan.json --plan-version 1
# Review the printed new version and approve it:
uv run --locked evidenceforge-research --offline --resume THREAD_ID --approve-plan 2
# Or reject:
uv run --locked evidenceforge-research --offline --resume THREAD_ID --reject-plan 1
```

Owner and data directory must match the starting run when overriding defaults. Resume
without a decision leaves the approval interrupt pending. Existing --cancel and --pause-after
controls remain available for offline and Gemini research. Every finalized run now saves report.json
beside report.md. report.json is an allowlisted user export, not the internal state.json
checkpoint. It contains final report metadata, graph/evidence locators, audit and usage,
with explicit synthetic/document and model labels.

## Open gates

- Gemini 3.8 still returns HTTP 503. The authorized `gemini-3.5-flash-lite` fallback is configured
  and verified for generation and durable approval/resume. Provider availability can change.
- Historical Gemini runs without durable receipts cannot be resumed; create a new run.
- No live web research, new external API/MCP adapter or deployment is added here.
- Missing assignment PDF/rubric reconciliation and human research-quality comparisons remain open.
- Exact retained quotations and locator checks do not independently verify source truth.
- Uploads have bounded parsing, but this localhost demo is not an untrusted public upload service.

## Verification

**Local workbench complete; Gemini recovery verified, 2 October 2026.**

- Final full regression: **314 passed in 549.94 seconds**, no failures or skips.
- Actual Streamlit AppTest: create, save edited plan, renewed approval, report/claim inspection,
  downloads, scope change and the timeline/coverage/usage panels passed.
- Edit/update checks passed: no repeat planning/retrieval calls, stale versions rejected,
  subquestion cap enforced, cancelled/finalized plans protected, foreign timeline/export denied.
- Paid controls now use durable scoped model receipts. A live plan -> edit version 2 -> approve
  across fresh services -> report -> terminal reconnect completed with five successful Gemini
  calls and 5,692 provider-reported tokens. CLI reconnect and UI facade reads also passed.
- Separate-process CLI approval and edit-version-two approval/resume passed.
- Ruff and formatting passed; strict mypy passed for 65 source files. Third-party Streamlit
  internals are excluded from type traversal; our UI and application code remain checked.
- uv lock check passed (91 packages); optional Streamlit version tested: 1.64.0.
- Local server health: HTTP 200 at 127.0.0.1:8501.
- Distribution source/entry-point/private-file checks are recorded in package.json.

The regression exposed an early-planning-failure status bug introduced by approval routing:
it is fixed, preserving failed rather than insufficient_evidence. A checkpoint reader issue
was also fixed by excluding LangGraph internal routing channels before strict state validation.
Progress uses durable checkpoints rather than redundant per-step progress-file writes.

Artifacts: .evidenceforge/verification/phase8/ (ignored by Git). Test runs overlap; their
counts are not added together. See PROGRESS.md for the executed history.

Phase 9 has not started.

## Gemini durable recovery repair — 2 October 2026

The generateContent endpoint rejected the original detailed Pydantic schemas. The adapter now
omits unsupported validation metadata in provider schemas and converts finite purpose patterns
to enums. Full local schemas, ID checks and citation gates are retained. Google guidance:
https://ai.google.dev/gemini-api/docs/structured-output.

Model-call SQLite ledgers are scoped to owner/run/model and immutable budget. A transaction
reserves allowance before HTTP. Validated responses and sanitized usage are committed before
returning to the graph. Exact logical requests reuse completed results after restart. A pending
call after a crash blocks automatic spending; failed calls also cannot silently replay. Private
keys and raw request bodies are absent from receipts; response text remains in ignored local data.
The registered profile requires ledger version 1, so older paid runs fail configuration checks.

UI offers explicit Gemini selection and separate durable provider usage counters. CLI resumes
use the registered model and original request/options/budget. Offline and Gemini workflows cannot
be switched during resume. Cost remains unknown until a verified pricing policy exists.

Repair checks: 35 adapter/approval/UI regression cases passed, plus 5 final receipt/schema cases
(overlapping counts). Live artifacts: `.evidenceforge/verification/gemini-resume/live.json`.
Full Phase 8 regression totals above describe the prior baseline; they were not rerun for this repair.
