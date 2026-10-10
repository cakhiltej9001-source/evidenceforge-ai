# EvidenceForge status  14 10 October 2026

The local workbench retains durable SQLite data. The [public Streamlit demo](https://evidenceforge-ai-akhiltej.streamlit.app/) uses offline fixtures and temporary visitor storage. Hosting remains **free only ( b90/month)**. The local Gemini model is now `gemini-3.1-flash-lite`; existing run registrations and paid-call receipts retain their recorded models.

## Phases

| Phase | Work | Current status |
|---|---|---|
| 0 | Handoff and original assignment | Complete; all 23 supplied PDF pages reconciled |
| 1 | Package, configuration, schemas, state | Implemented and tested |
| 2 | Manager, planner, context, queries | Implemented; plan review remains important for scope |
| 3 | Retrieval, snapshots, provenance | Implemented; earlier Tavily and Wikipedia access verified |
| 4 | Coverage, synthesis, critic, report | Implemented; current quotation, duplicate, and missing-percentage corrections described below |
| 5 | Documents, checkpoints, restart | Implemented locally; optional OCR is bounded |
| 6 | Ranking, inspection, numeric comparison | Implemented for documented rules and grammar |
| 7 | Budgets, cancellation, receipts, tracing | Implemented; one synthetic remote trace was verified |
| 8 | UI, approval, exports | Implemented; hosted fixture downloads and visitor isolation verified |
| 9 | Evaluation and Gemini comparison | Controlled 20-case comparison and AI review complete; independent human review remains open |
| 10 | API, containers, deployment | Local durable operation and private Docker CI verified; public fixture demo deployed; hosted durability deferred under free-only choice |
| 11 | Setup and submission materials | Prepared; external acceptance has not been assessed |

## Current Gemini verification

A fresh, bounded check used normalized Atmosphere sections fetched from [NASA Earth](https://science.nasa.gov/earth/facts/) and [NASA Mars](https://science.nasa.gov/mars/facts/). This was a two-source, one-topic probe with frozen section excerpts, not open web search or an independent benchmark.

- The first 12-call diagnostic found that the model shortened quotations in the Python documentation case. Exact citation auditing rejected those claims. A versioned selector now asks Gemini for evidence IDs and copies full passages from retained snapshots. Historical saved runs keep their original request contract.
- The earlier NASA attempt paused for plan review until its five-minute run deadline expired; it saved no evidence. The separate, explicitly approved **six-call** run used a longer deadline. All six structured roles succeeded with HTTP 200 responses. It retained two NASA sources, six passages, exact locators, and a partial report. Terminal reconnect made no new call; prior benchmark ledgers did not change.
- Review of that report found a repeated Mars claim and a false positive for Mars gas-percentage coverage. The saved report remains a record of that result. Current code removes repeated evidence selections and requires a numeric percentage in linked evidence when a criterion asks for percentages. An offline replay of the same saved model decisions produced two distinct, exactly cited claims and explicitly disclosed missing Mars percentages, with **zero additional provider calls**. The replay's critic approval was scripted, so it is not a new live Gemini result.
- The quote-aware critic has a new registered contract version. Its live call no longer objected to using full quotations; it correctly flagged the duplicate. Old profiles still select their old critic request.

The [AI review and measured probe](evaluation/LIVE_SOURCE_PROBE_2026-10-10.md) records the rubric, failed cases, and semantic findings.

The live result establishes that the currently selected model can complete all six structured roles on this controlled case. The latest duplicate and percentage safeguards have offline regression and replay evidence; a fresh live report after those safeguards remains untested. This probe does not establish broad semantic accuracy or independent human sign-off. Cost in dollars is unknown. The 12-call and six-call diagnostic allowances are exhausted and separate from earlier benchmark ledgers.

## Engineering and operational status

[Exact-source CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38018900500) passed on `aa294b2` at **08:29:38 IST on 10 October 2026**: **474 tests in 38.25 seconds**, Ruff lint/format, strict mypy on 85 source files, package build, official Render schema, offline persistence and deployment smoke, and the Docker jobs. Docker checked resource limits, nonroot execution, checkpoint reconnect, backup/restore, UI health, and authenticated gateway access.

The local `.env` holds provider credentials and is ignored by Git. The public Streamlit deployment remains fixture only, with no paid Gemini or Tavily calls, uploads, or persistent visitor storage.

## Remaining work

- Independent human review and a larger real-source semantic-quality study remain optional validation. AI review is labeled as AI review.
- The post-correction report path has offline replay and CI evidence; an additional live run would need a separate approved call allowance.
- Durable hosted storage and jobs remain deferred by the free-only hosting decision. Local durable storage is the supported mode.

See the [8 October phase record](FINAL_STATUS_2026-10-08.md), [setup](submission/SETUP.md), [limitations](submission/LIMITATIONS.md), and the private local verification artifacts under `.evidenceforge/verification/gemini-structured-2026-10-09`.
