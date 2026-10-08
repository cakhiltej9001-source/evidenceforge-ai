# Final local project status — 6 October 2026

> Current policy, 8 October 2026: hosting is free only (INR 0/month), superseding the earlier INR 5 allowance. The public Streamlit fixture demo is deployed. See [current status](FINAL_STATUS_2026-10-08.md); dated results below remain historical.

The user selected **local durable storage** after confirming a **₹5/month**
hosting cap. Public Render deployment is deferred by that choice. No paid Render
resource was created. The owner subsequently requested a public Streamlit demo,
now live at [EvidenceForge](https://evidenceforge-ai-akhiltej.streamlit.app/).
It uses synthetic fixtures and temporary visitor-scoped storage; the full local
workbench retains durable storage. The private repository remains private.

## Phase status

| Phase | Description | Current status |
|---|---|---|
| 0 | Plan, handoff and original assignment mapping | Complete; all 23 supplied PDF pages reconciled |
| 1 | Locked Python package, configuration, schemas and shared state | Complete |
| 2 | Manager, planner, scoped context and query generation | Complete for the local workflow; model-generated plans still need review |
| 3 | Retrieval, snapshots, evidence extraction and provenance | Complete; live Tavily and Wikipedia fallback verified |
| 4 | Coverage loops, synthesis, critic, citation checks and reports | Complete; bounded partial and insufficient outcomes are disclosed |
| 5 | Document ingestion, SQLite checkpoints and restart | Complete; fresh-process local reconnect verified |
| 6 | Claim inspection, ranking and scoped numeric disputes | Complete within the documented numeric grammar and heuristic limits |
| 7 | Guardrails, budgets, cancellation, durable receipts and tracing | Complete for local operation; production input review, fallback and retention controls implemented |
| 8 | Streamlit UI, plan approval/editing, progress and exports | Complete for local use; container browser authentication verified in CI |
| 9 | Frozen benchmark, Gemini comparison and delegated review | Completed controlled comparison and AI review; limitations below remain unclaimed research validation |
| 10 | External energy source, container checks and deployment | Local durability and Docker CI verified; public Streamlit fixture demo deployed and exercised; paid Render hosting deferred |
| 11 | Setup, architecture, demo, checklist and evaluation materials | Prepared and updated with measured results; external grading/submission acceptance is not asserted |

## Completed verification

- Public Streamlit deployment completed a plan/approval/report flow with two
  retrieval passes, two retained findings, two citation checks and no tool errors.
  Public sharing was checked after saving. The public entrypoint uses no paid
  providers or uploaded private data; visitors receive separate generated scopes.
  [Runtime CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37505393414)
  passed on `6fb5241c1dd36e18a7ae86ba2b61fee41732fe0f`. See
  [deployment details and screenshot](STREAMLIT_CLOUD.md).

- [Private CI run](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37485512573)
  passed both Python and Docker jobs on source
  `0f070d134491e2b2a161ecdfdaf987daec2ac904`, completing at
  **20:44:20 IST on 6 October 2026**. **373 tests passed**; lint, formatting,
  strict typing, package build and official Render schema checks passed.
- Docker verified UID 10001, 512 MB/half-CPU operation, persistence across fresh
  containers, fresh-volume synthetic backup/restore, health and authentication.
  Anonymous browser/upload/media/WebSocket requests and wrong passwords were
  rejected. Authenticated root and public health checks passed with `RENDER=true`.
- Fixed the container's UI launcher arguments and process supervision. The
  future Render template requires both the Caddy bcrypt secret and the app's
  PBKDF2 secret; these are not published with source.
- Today's local offline research/export and separate-process reconnect passed.
  Saved work remains under the ignored `.evidenceforge` directory. Keep that
  complete directory when backing up or moving the local installation.
- Actual Tavily acquisition/full-pipeline recovery was verified on 5 October.
  Today's fallback used a simulated primary failure and one live Wikipedia GET:
  five sources, seven retained passages, completed report, zero Gemini/Tavily calls.
- The corrected Gemini comparison saved all **40 rows** for 20 cases using
  **136/140 calls**, all HTTP 200 and validated, on `gemini-3.5-flash-lite`.
  Historical ledgers remain separate at **26/30** and **28/40**.
- The [comparison report](evaluation/V2_COMPARISON_REPORT_2026-10-06.md) and
  [40-row AI review](evaluation/V2_AI_REVIEW_2026-10-06.json) record the findings,
  source/result identities and review limitations.

## Remaining limitations and optional future work

No missing credential, additional Gemini allowance or hosting decision blocks the
selected local deliverable. These checks do **not** establish general research
accuracy or source truth:

- Both approaches retained the two supplied factors in all 16 factor cases.
  Baseline quotations omit fixture labels and sometimes punctuation; this
  triggers revision under the complete-sentence rubric, not a factual-factor failure.
- Both approaches flagged the two conflicts and abstained in both empty-source
  cases. The workflow conflict reports remain partial within their approved bounds.
  Case 18 also adds unrequested monthly planning criteria; review plans before
  approval. No conflict was guessed away.
- Independent human validation and a broader real-source benchmark have not been
  performed. The user-delegated review is explicitly an AI review. Neither human
  review nor hosted deployment is mandated by the supplied PDF.
- Remote LangSmith export, scanned-PDF OCR, broad semantic contradiction handling,
  distributed jobs and hosted durability are unverified or outside this local scope.
- Any separate instructor/competition delivery rules would need to be supplied
  before claiming external submission acceptance.

## Run locally

```powershell
cd "C:\Users\AKHILTEJ\Documents\ChatGPT\AI Research agent"
uv run --locked --extra ui evidenceforge-ui
```

Open `http://127.0.0.1:8501`. Choose offline reasoning for a provider-free demo.
Gemini and live web choices consume their configured allowances when explicitly
started. Stop the UI with Ctrl+C; restarting preserves saved local research.

Older phase records retain their historical outcomes. This document supersedes
earlier missing-PDF, missing-credential, blocked-comparison and hosting-budget notes.
