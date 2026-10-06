# Tavily live verification — 5 October 2026

Completed **08:04:17 IST** (02:34:17 UTC) on source `b700b5e`.
The user supplied the credential and delegated the full live check.
The credential is stored only in the ignored local `.env`; no key is included here.

## Measured result

- Credential check: one basic search, three results, one reported Tavily credit.
- Full research: one basic search, five live sources, 34 retained passages,
  34 quotation claims and 34 supported exact quotation checks.
- Run status: `completed`, stop `sufficient`, one retrieval pass, zero rewrites;
  no tool errors. Execution took 14.43 seconds.
- Paused after extraction and resumed using a fresh service. A second fresh service
  reopened the terminal checkpoint with identical state; the saved ledger retained
  exactly one search request. Recovery made no additional provider request.
- Export correctly identifies `live_sources`; source snapshots, passage locators,
  report, export, checkpoint and sanitized verification are saved locally.
- **One credit for this full check; two credits including credential verification.**
  **Zero Gemini calls**; prior Gemini ledgers remain unchanged.

Run: `run_87c056e986b94886974032b599a8fd4c`.
Thread: `thread_e4b842b3427442fc81549e5ed556ed1c`.
Ignored artifacts are under `.evidenceforge/verification/tavily-full-research-2026-10-05/`.
The saved report is under that directory's `reports/run_87c056e986b94886974032b599a8fd4c/report.md`.

## Verification boundary

This closes Tavily credential, actual acquisition and full pipeline integration gates.
The check used an explicit one-question plan and deterministic fixture reasoning;
coverage is lexical and synthesis repeats retained passages. The inspected report
includes website navigation/newsletter boilerplate and broad quoted chunks. Passing
exact quotation checks establishes retained-text support, not relevance, source truth,
or the quality of a semantic solar/wind comparison. Those research-quality gates
remain open. This run does not verify combined real Tavily/Gemini execution, live
mixed web/API/documents together, hosted persistence or independent benchmark labels.
Existing mocked integration covers mixed-source behavior.

Render API access is [subsequently verified](RENDER_ACCESS_VERIFICATION_2026-10-05.md).
Persistent deployment, repository connection, access choice/spend cap, independent
human review and incremental production guidance remain pending. No runtime implementation was changed here.
