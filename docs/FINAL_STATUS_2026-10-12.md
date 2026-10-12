# EvidenceForge status - 12 October 2026

The local workbench retains durable SQLite data. The [public Streamlit demo](https://evidenceforge-ai-akhiltej.streamlit.app/) uses offline fixtures and temporary visitor storage. Hosting remains **free only (INR 0/month)**. New local Gemini runs use `gemini-3.1-flash-lite`.

## Phases

| Phase | Work | Current status |
|---|---|---|
| 0 | Handoff and original assignment | Complete; all 23 supplied PDF pages reconciled |
| 1 | Package, configuration, schemas, state | Implemented and tested |
| 2 | Manager, planner, context, queries | Implemented; plan review remains important for scope |
| 3 | Retrieval, snapshots, provenance | Implemented; earlier Tavily and Wikipedia access verified |
| 4 | Coverage, synthesis, critic, report | Implemented; combined live workflow and exact citations verified; report-quality limits remain |
| 5 | Documents, checkpoints, restart | Implemented locally; optional OCR is bounded |
| 6 | Ranking, inspection, numeric comparison | Implemented for documented rules and grammar |
| 7 | Budgets, cancellation, receipts, tracing | Implemented; one synthetic remote trace was verified |
| 8 | UI, approval, exports | Implemented; hosted fixture downloads and visitor isolation verified |
| 9 | Evaluation and Gemini comparison | Controlled 20-case comparison and AI review complete; independent human review remains open |
| 10 | API, containers, deployment | Local durable operation and private Docker CI verified; public fixture demo deployed; hosted durability deferred under free-only choice |
| 11 | Setup and submission materials | Prepared; external acceptance has not been assessed |


## Latest live verification

The second fresh Gemini/Tavily run completed at **15:08:34 IST on 10 October**;
the saved result was reviewed on 11 October. It used **six Gemini calls and one
Tavily search (one credit)**. All six structured roles succeeded, including
synthesis and critic. The workflow returned `completed` / `sufficient`,
retaining three NASA sources, 15 passages and three distinct claims.

All three claims exactly match retained passages and have complete supported
citation audits. An offline check verified all 15 locators and restored the
identical terminal result in a fresh process with **zero network attempts**.
The review made no new provider calls. Known Gemini usage was **40,374 tokens**;
dollar cost is unknown.

The [measured run and AI review](LIVE_GEMINI_TAVILY_REVIEW_2026-10-11.md) records
both the successful execution and answer-quality limits. The report includes
passages cut in the middle of words/sentences, unrelated equations and download
metadata. It quotes differing Mars percentages without explaining their context.
All sources belong to NASA; broad factual accuracy and human sign-off remain
unclaimed.

The [first combined attempt](GEMINI_TAVILY_VERIFICATION_2026-10-10.md) failed
synthesis because Gemini returned a malformed evidence ID. That result and its
5/6 Gemini, 1/1 Tavily usage remain preserved. The new campaign used its own 6/6
Gemini and 1/1 Tavily allowance. No source code changed between the two runs;
the successful repeat does not eliminate the earlier output-validation risk.
Historical benchmark and diagnostic ledgers were unchanged.

## Engineering and operation

The published [CI on 714818f](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38040707517)
passed both Python and container jobs. The unchanged source has **474 passing
tests**, Ruff lint/format, strict mypy, package build, Render schema validation,
deployment smoke, Docker persistence, backup/restore and authenticated gateway
checks. The [exact source result](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38018900500)
records the full test count.

Tavily access, the fresh combined workflow, synthetic LangSmith counter
delivery/readback, and hosted fixture downloads have verification records.
Credentials and full private verification artifacts remain ignored by Git.
The public demo remains fixture only; durable research storage is local.

## Remaining work

- Improve report readability and explain or explicitly qualify differing
  source values. Broader planner and semantic checks remain roadmap work.
- Broader real-source quality testing, independent human review and independent
  OCR accuracy review remain optional validation.
- Durable hosted storage and background jobs remain deferred under the
  free-only hosting choice.
- CI maintenance remains: checkout-action deprecation and the upcoming
  `ubuntu-latest` image migration were reported by GitHub.

The live provider and full-workflow execution check is complete for this case.
General reliability and semantic accuracy are not established by one run.
See [setup](submission/SETUP.md), [limitations](submission/LIMITATIONS.md), and
the [10 October historical status](FINAL_STATUS_2026-10-10.md).
