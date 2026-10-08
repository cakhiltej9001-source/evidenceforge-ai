# Current project status - 8 October 2026

The full workbench uses local durable storage. The public
[Streamlit fixture demo](https://evidenceforge-ai-akhiltej.streamlit.app/) is
deployed with temporary visitor storage, no uploads and no paid providers.
Paid Render hosting remains deferred under the selected INR 5/month cap;
no paid Render resource was created.

## Phase status

| Phase | Description | Status |
|---|---|---|
| 0 | Plan, handoff and assignment mapping | Complete; all 23 supplied PDF pages reconciled |
| 1 | Locked package, configuration, schemas and state | Local implementation complete |
| 2 | Manager, planner, context and queries | Local implementation complete; annual-scope safeguard added; plans still need review |
| 3 | Retrieval, snapshots and provenance | Local implementation complete; historical Tavily/Wikipedia access verified |
| 4 | Coverage, synthesis, criticism and reports | Local implementation complete; partial and insufficient outcomes disclosed |
| 5 | Documents, checkpoints and restart | Local implementation complete; optional bounded OCR and DOCX row retention added |
| 6 | Ranking, inspection and numeric disputes | Local implementation complete within explicit grammar; generation wording extended |
| 7 | Budgets, cancellation, receipts and tracing | Local implementation complete; synthetic counters-only remote delivery verified |
| 8 | UI, plan approval and exports | Local implementation complete; export-byte checks added; actual browser download not observed |
| 9 | Benchmark, Gemini comparison and review | Controlled comparison and AI review complete; independent human/semantic validation unclaimed |
| 10 | API, containers and deployment | Local durability and historical Docker checks verified; public fixture deployed; paid Render deferred |
| 11 | Setup, architecture and evaluation materials | Updated with current implementation and measured limits; external submission acceptance unclaimed |

## Current verification

- Ruff lint/format checks passed. Strict mypy passed for **85 source files**.
- The full regression suite and current GitHub CI are **in progress**. Historical
  passing suites in [6 October status](FINAL_STATUS_2026-10-06.md) remain dated
  evidence; they do not establish a pass for the current source revision.
- On 8 October, the public demo returned **HTTP 200 with fresh cookies**.
  An actual browser report download has not been observed; the browser helper failed with a Windows sandbox setup error.
- LangSmith synthetic upload and exact completed-span readback passed on 8 October: one tracked receipt, one verified receipt and zero omitted/unverified receipts. The key stays in ignored local configuration. See [verification](LANGSMITH_VERIFICATION_2026-10-08.md). The explicit probe sends synthetic counters
  and requires exact completed-span readback.
- **Zero new Gemini/Tavily calls** were made for these additions. The corrected
  comparison remains **136/140** approved calls; historical ledgers remain
  **26/30** and **28/40**, separately recorded.

## Implemented additions

Generated plans reject new subannual requirements for annual/year requests while
respecting explicit breakdown preferences. Date/seasonal exemptions keep this a
bounded scope check. Numeric extraction accepts explicit electricity-generation
wording while preserving entity, timeframe, population, condition and unit checks.

Optional PDF OCR requires Python 3.12 and the `ocr` extra; retained quotations
refer to labeled machine transcripts and require original-page checks. DOCX rows
retain cell alignment and locators. A separate SQLite CLI queue persists offline
fixture jobs, with explicit plan approval and lease recovery on one local
filesystem. Paid/live profiles are rejected.

Export regressions inspect Markdown/JSON download bytes, and download buttons
skip unnecessary UI reruns.
Custom LangSmith spans allowlist counters; the synthetic CLI uses a fixed project,
full sampling and receipt readback. Implementation and local mechanics do not
establish actual browser download success. The fixed synthetic remote trace was separately verified.

## Retained public-source replay

The **7 October** run used five retained sources: four EIA pages and one
Utility Dive page. The available case retained 30 claims/evidence passages with
30 exact locators. A duplicate input increased results to six while retaining the
same five sources and 30 passages. The missing-aspect case stayed partial with
20 claims and one gap; the empty case produced zero claims and insufficient
evidence. All five mechanical checks were true, with zero provider calls.

See the [measured replay report](evaluation/RETAINED_PUBLIC_REPLAY_2026-10-07.md)
and [raw JSON](evaluation/RETAINED_PUBLIC_REPLAY_2026-10-07.json).
Scripted reasoning over one corpus establishes neither source truth, general
research accuracy nor independent human validation.

[Setup](submission/SETUP.md), [requirements](submission/REQUIREMENTS.md) and
[limitations](submission/LIMITATIONS.md) describe the operational boundaries.
Earlier phase records retain their dates, ledgers and then-current results.
