# EvidenceForge status - 12 October 2026

The local workbench retains durable SQLite data. The [public Streamlit demo](https://evidenceforge-ai-akhiltej.streamlit.app/) uses offline fixtures and temporary visitor storage. Hosting remains **free only (INR 0/month)**. New local Gemini runs use `gemini-3.1-flash-lite`.

## Phases

| Phase | Work | Current status |
|---|---|---|
| 0 | Handoff and original assignment | Complete; all 23 supplied PDF pages reconciled |
| 1 | Package, configuration, schemas, state | Implemented and tested |
| 2 | Manager, planner, context, queries | Implemented; plan review remains important for scope |
| 3 | Retrieval, snapshots, provenance | Implemented; fresh domain-filtered Tavily search and exact locators verified |
| 4 | Coverage, synthesis, critic, report | Implemented; combined live workflow and exact citations verified; report-quality limits remain |
| 5 | Documents, checkpoints, restart | Implemented locally; optional OCR is bounded |
| 6 | Ranking, inspection, numeric comparison | Implemented for documented rules and grammar |
| 7 | Budgets, cancellation, receipts, tracing | Implemented; fresh synthetic remote trace delivered and read back |
| 8 | UI, approval, exports | Implemented; hosted fixture downloads and visitor isolation verified |
| 9 | Evaluation and Gemini comparison | Controlled 20-case comparison and AI review complete; independent human review remains open |
| 10 | API, containers, deployment | Local durable operation and private Docker CI verified; public fixture demo deployed; hosted durability deferred under free-only choice |
| 11 | Setup and submission materials | Prepared; external acceptance has not been assessed |


## Latest live verification

The second fresh **12 October** campaign completed all six Gemini roles and one
Tavily search (one credit), retaining three NASA sources, 15 passages and two
distinct exact quoted claims. Gemini usage was **27,714 tokens**; dollar cost
is unknown. The workflow completed with sufficient coverage and critic approval.

All claim audits and locators passed. An offline fresh-process reconnect restored
identical terminal state with **zero network attempts**. LangSmith passed fresh
synthetic counter-span delivery/readback; no research payload was uploaded.

The [measured fixes and AI review](REMAINING_FIXES_2026-10-12.md) records compact
Gemini selection aliases, structured Tavily domain filtering, sentence-boundary
extraction and report presentation changes. Both 12 October campaigns exhausted
their separate 6/6 Gemini and 1/1 Tavily caps. The first failed workflow and its
successful sixth-call compact-schema diagnostic remain preserved.

The new report still contains a flattened PDF table and unrelated exercise text,
and omits explicit enumeration of missing requested percentages. Exact quotation
support and API execution do not establish semantic completeness. The
[10 October run](LIVE_GEMINI_TAVILY_REVIEW_2026-10-11.md) remains historical.

## Engineering and operation

The published [source CI on afcad1c](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38241087132)
passed both Python and container jobs. The source has **482 passing tests**,
Ruff lint/format, strict mypy, package build, Render schema validation,
deployment smoke, Docker persistence, backup/restore and authenticated gateway
checks. The 58 focused regression tests also passed locally.

Tavily access, the fresh combined workflow, synthetic LangSmith counter
delivery/readback, and hosted fixture downloads have verification records.
Credentials and full private verification artifacts remain ignored by Git.
The public demo remains fixture only; durable research storage is local.

## Remaining work

- Table-aware extraction, directly relevant passage selection and broader
  planner/semantic coverage checks remain roadmap work. Current presentation
  and unresolved-value qualification fixes are implemented.
- Broader real-source quality testing, independent human review and independent
  OCR accuracy review remain optional validation.
- Durable hosted storage and background jobs remain deferred under the
  free-only hosting choice.
- CI action and runner maintenance is implemented in the new pipeline.

The live provider and full-workflow execution check is complete for this case.
General reliability and semantic accuracy are not established by one run.
See [setup](submission/SETUP.md), [limitations](submission/LIMITATIONS.md), and
the [10 October historical status](FINAL_STATUS_2026-10-10.md).
