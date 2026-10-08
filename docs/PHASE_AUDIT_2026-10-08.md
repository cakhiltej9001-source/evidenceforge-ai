# Entire phase audit - 8 October 2026

Reviewed phases 0-11 against the supplied assignment mapping, current implementation,
regressions and saved verification. The selected product is a durable local
workbench plus a free public fixture demo. No new provider requests were made
during this audit, and historical benchmark allowances were preserved.

## Phase-by-phase result

| Phase | Audited work | Result |
|---|---|---|
| 0 | Handoff and all 23 original-PDF pages | Mapping complete; no separate grading rubric or delivery rule supplied |
| 1 | Locked dependencies, settings, schemas, state | Implementation present; secrets excluded and redacted |
| 2 | Manager/planner/context/queries | Implemented; dated/seasonal scope fix already verified; other scope drift still needs plan review |
| 3 | Retrieval, snapshots, acquisitions, provenance | Implemented; source access records are historical, not current availability guarantees |
| 4 | Coverage, synthesis, critic, citations and report | Found and fixed the all-Summary/empty-Key-Findings edge; new regression checks current and frozen behavior |
| 5 | Documents, checkpoints, restart, OCR/table handling | Implemented within documented format, transcript and local durability limits |
| 6 | Ranking, inspection, numeric disputes | Implemented for explicit supported grammar; broad semantic contradictions remain outside that boundary |
| 7 | Budgets, cancellation, durable model receipts, tracing | Controls implemented and tested; synthetic remote trace delivery/readback already verified; current Gemini availability remains a follow-up |
| 8 | Local UI, approval, editing, reconnect, exports | Implemented; hosted Chromium downloads and fresh-visitor isolation already verified |
| 9 | Frozen benchmark, matched Gemini comparison, AI review | Controlled study complete with retained answers; independent human/general research validation remains unclaimed |
| 10 | API, Docker, backups, authenticated gateway, public demo | Implemented and previously CI-verified; paid durable hosting is outside the user's free-only choice |
| 11 | README, setup, architecture, evaluation and submission material | Active stale test counts and scope wording corrected; historical phase records preserved |

## Concrete fix

A schema-valid synthesis could assign every supported factual claim to Summary.
The existing report always included a Key Findings heading, but the section could
be empty even when the run completed. Current quality-input version 2 now fills
an empty Key Findings section with the existing factual claim IDs. It creates no
new statements or citations; the usual critic and citation audit still apply.

The regression uses a custom model that places all claims in Summary, then checks
that the completed current-version report contains both exact supported findings.
It also verifies unchanged version-1 behavior for frozen historical comparisons.

Source: [synthesis](../src/evidenceforge/nodes/quality.py).
Regression: [report behavior](../tests/test_research.py).
Verification of the changed implementation will be recorded below after CI.

## Remaining operational check

The saved local model is still `gemini-3.5-flash-lite`; its latest basic generation
request returned HTTP 503. The lighter `gemini-3.1-flash-lite` returned a correct
fixed text response, but that probe did not use the structured adapter's schema,
thinking settings or research workflow. Current structured generation therefore
remains unverified. Historical successful structured runs are preserved.

Changing a default for new runs must not silently switch resumed paid checkpoints:
registered runs retain their saved model and failed/uncertain-call protections.
See [latest Gemini diagnostic](GEMINI_API_TEST_2026-10-08.md).

## Optional validation and extensions

Independent human sign-off, a broader combined live Gemini/Tavily research-quality
study, general semantic contradiction/deduplication, distributed cloud workers and
any separate external grading acceptance remain unclaimed. They are not missing
baseline mechanics mandated by the supplied PDF. Full-workbench durable data stays
local; the public fixture demo uses temporary visitor storage.

[Current status](FINAL_STATUS_2026-10-08.md) and
[requirement traceability](submission/REQUIREMENTS.md) retain the detailed scope.
