# Current project status - 8 October 2026

The full workbench uses local durable storage. The public
[Streamlit fixture demo](https://evidenceforge-ai-akhiltej.streamlit.app/) is
deployed with temporary visitor storage, no uploads and no paid providers.
Hosting is **free only (INR 0/month)**, replacing the earlier INR 5/month allowance.
The default Render blueprint also selects free compute without a persistent disk.

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
| 8 | UI, plan approval and exports | Local UI complete; actual hosted fixture downloads and fresh-visitor isolation verified |
| 9 | Benchmark, Gemini comparison and review | Controlled comparison and AI review complete; independent human/semantic validation unclaimed |
| 10 | API, containers and deployment | Local durability and current Docker checks verified; public fixture deployed; free hosting only |
| 11 | Setup, architecture and evaluation materials | Updated with current implementation and measured limits; external submission acceptance unclaimed |

## Current verification

- [Exact source CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37750655847) passed both Python and Docker jobs on `a89e4ef00844acc5f1b2936c98751a69021c2929`, completing at **14:04:55 IST on 8 October 2026**.
- **457 tests passed in 28.27 seconds** on Linux/Python 3.12. Ruff lint/format, strict mypy (85 source files), locked installation with UI/OCR extras, wheel/sdist build, official Render schema and deployment smoke all passed.
- Docker verified nonroot UID, 512 MB/half-CPU operation, fresh-container checkpoint reconnect, fresh-volume backup/restore, UI health and authenticated gateway rejection of anonymous upload/media/WebSocket requests.
- The local Windows OCR suite passed **14 tests in 50.60 seconds**, including actual image-only PDF recognition, transcript disclosure, credential isolation and timeout cleanup. The complete Windows run hit process/import delays and a 15-minute host limit; the full regression evidence above is from Linux CI.
- [Actual hosted browser downloads](HOSTED_DOWNLOAD_VERIFICATION_2026-10-08.md) passed all eight checks at **14:13:49 IST**: saved `report.md` (1,263 bytes) and `report.json` (22,939 bytes), verified completed fixture contents, and confirmed a fresh browser context had no saved run or report downloads. [Browser CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37751643343) used Chromium without credentials or paid providers.
- LangSmith synthetic upload and exact completed-span readback passed: **one tracked receipt, one verified receipt, zero omitted/unverified receipts**. The key stays in ignored local configuration. See [verification](LANGSMITH_VERIFICATION_2026-10-08.md).
- **Zero new Gemini/Tavily calls** ran. The corrected comparison remains **136/140**; historical ledgers remain **26/30** and **28/40**, separately preserved.
- All **159 local documentation links** resolved. **209 tracked files** were checked against all three configured private credentials with no matches; `.env` is excluded from Git.

## Implemented additions

Generated plans reject new subannual requirements for annual/year requests while
respecting explicit breakdown preferences. Date/season context allows relevant
supporting measurements without exempting unrelated finer breakdowns. This remains
a bounded scope check. Numeric extraction accepts explicit electricity-generation
wording while preserving entity, timeframe, population, condition and unit checks.

Optional PDF OCR requires Python 3.12 and the `ocr` extra; retained quotations
refer to labeled machine transcripts and require original-page checks. DOCX rows
retain cell alignment and locators. A separate SQLite CLI queue persists offline
fixture jobs, with explicit plan approval and lease recovery on one local
filesystem. Paid/live profiles are rejected.

Export regressions inspect Markdown/JSON download bytes, and download buttons
skip unnecessary UI reruns.
Custom LangSmith spans allowlist counters; the synthetic CLI uses a fixed project,
full sampling and receipt readback. Actual hosted browser exports and the fixed
synthetic remote trace were separately verified; each check retains its measured scope.

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

## Additional free verification - 8 October 2026

- The dated/seasonal planning correction passed **35 targeted tests in 2.37 seconds**. Date context no longer bypasses all temporal scope checks; explicit preferences and chronology wording remain supported.
- [Two retained corpora](evaluation/RETAINED_CORPORA_2026-10-08.md) passed **all nine checks** with zero provider calls. EIA/Utility Dive full text retained 30 exact cited claims and completed; Wikipedia search excerpts retained nine exact cited claims and correctly stayed partial with a wind-evidence gap. Excerpt scope and corpus isolation were preserved.
- These measurements do not establish broad semantic accuracy or independent human review.

## Remaining optional validation and extensions

- Independent human sign-off and a broader combined live Gemini/Tavily research-quality benchmark have not been performed. The existing review is explicitly AI review.
- General semantic contradiction/deduplication and distributed cloud workers remain broader extensions. Current numeric comparisons and local fixture queue have explicit bounded behavior.
- External submission/grading acceptance cannot be claimed without any separate delivery rules. These are not requirements stated by the supplied PDF.

No required implementation or credential setup remains pending for the selected local workbench and public fixture demo. Optional validation and extension limits are listed above.

[Setup](submission/SETUP.md), [requirements](submission/REQUIREMENTS.md) and
[limitations](submission/LIMITATIONS.md) describe the operational boundaries.
Earlier phase records retain their dates, ledgers and then-current results.
