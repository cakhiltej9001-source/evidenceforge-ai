# Original assignment implementation fixes — 5 October 2026

The user supplied the original 23-page assignment and instructed Codex to continue.
The [original audit](submission/ORIGINAL_PDF_RECONCILIATION.md) preserves the source
hash and initial findings against `93b320d`. This update implements its highest
priority runtime gaps; the original PDF remains unmodified and outside source upload.

## Completed mechanics

| PDF mapping | Change | Verification boundary |
|---|---|---|
| B02, pages 2/5–6/10 | Opt-in Tavily web + GB energy API + selected documents in full research; CLI/UI controls; saved source choices | Real adapters with mocked HTTP exercise approval, edit, restart, owner isolation, receipt reuse, partial failure and cancellation; actual Tavily access remains unverified |
| B09, page 13 | 2–3 supported summary paragraphs, per-source evidence chunks/locators | Exact retained quotations remain audited; fewer supported claims produce a disclosed shorter summary |
| B05, pages 10–11 | Conservative literal working-set deduplication with source/acquisition/locator member metadata | Copies/full containment collapse only when question links are represented; complete exact-copy citations audited separately; distinct wording/qualifiers/partial overlaps preserved |
| Resource lifecycle | Factory-owned HTTP ports close on pause/completion, stale edit, resume mismatch and failure | Mock clients assert closed; caller-owned injected ports remain caller-owned |

No credentials or HTTP clients enter checkpoints. Default runs retain their prior
fixture/document profile; false live flags are omitted from profiles for compatibility.
`--offline` cannot enable or resume saved live-source acquisition. Missing Tavily keys
fail before planning or UI job submission. Saved live choices restore on reconnect.

The energy API returns GB generation shares in a half-hour including imports, not
annual/global output or MWh. Its prose is a deterministic projection of validated JSON.
Provider failure preserves other sources and yields a qualified partial result.
Grouping repeated text does not establish independent corroboration or source truth.

## Checks

- First mixed-source/report-focused run: **25 passed**, 242.22 seconds, Windows.
- Strict mypy: **passed**, 72 source files.
- Ruff lint and format: passed after implementation formatting.
- Deduplication end-to-end: one model passage, three retained original spans, two
  separately audited complete-quotation source citations; shorter span excluded
  from the complete claim citation.
- Final focused failure/cancellation/locator checks passed after correcting the
  fabricated test spans and using the established tool-error channel. Across the
  focused runs, **29 affected behavioral tests passed**. Full private CI is the
  remaining verification gate; its final result will be recorded below.

The tests use fabricated credentials and mocked HTTP; ordinary network is blocked.
No new Gemini, Tavily or NESO request ran for this change. Original Gemini accounting
remains 26/30; the separately approved extension remains 28/40. Frozen benchmark
labels/provider responses were not changed or rerun, and historical scores do not
measure this updated implementation.

## Remaining work

- Configure a Tavily credential here to verify actual live search/full research.
- Supply hosting account/target and spending cap for persistent deployment checks.
- Independent human validation and a defensible real research-quality comparison.
- Incremental production P02–P05: semantic input classification, ordered alternative
  search-provider fallback, lowest-score evidence eviction, and verified trace policy.
  These are distinct from the tested baseline mechanics; full production readiness
  is not claimed.

[Setup and reproduction](submission/SETUP.md) includes the exact CLI/UI controls.
