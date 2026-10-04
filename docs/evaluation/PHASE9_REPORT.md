# Phase 9 evaluation audit

Updated 4 October 2026, Asia/Calcutta.

## Status

The Phase 9 evaluation machinery and initial experiments are implemented. The
benchmark is **not yet human-validated**. The 20 labels are a Codex draft and need
independent review before any research-quality claim or final Phase 9 sign-off.

## Frozen dataset and protocol

`diverse_dataset.json` has SHA-256
`5e5c012fd1a612513a934e30469ba5a20b532e909732cfd47500f8453cdf4e89`.
It has 12 development and 8 held-out cases: 16 synthetic two-pass comparisons,
two disputes, and two empty-corpus abstentions. `config_manifest.json` records the
original freeze, source hashes, model, budgets, and 30-call Gemini cap. The
subsequent transport and accounting repairs are recorded in
`amendment_manifest.json`; the original manifest was preserved.

The fixture comparison uses the same frozen passages for one-pass and full-agent
runs, with a scripted model. The only workflow ablation is maximum retrieval
passes (1 versus 3). Each run allows at most 12 model calls and 8 searches.
The paid one-shot baseline uses `gemini-3.5-flash-lite` without retrieval, so
its uncited claims have citation, groundedness, and required-aspect scores `null`.
Two bounded full-agent probes used the same Gemini model and synthetic retrieval;
those probes are too few and incomplete for a quality comparison.

## Synthetic fixture results

All 40 case-variant runs executed. `missing_runs` is zero; `noncompleted_runs`
counts partial, insufficient, and failed outcomes. Full results are in
`.evidenceforge/evaluation/phase9_diverse/results.json` and `summary.json`.

| Partition | Variant | Cases | Completed | Noncompleted | Aspect coverage | Mean latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Development | One pass | 12 | 0 | 12 | 0.5 | 8.4084 s |
| Development | Full agent | 12 | 12 | 0 | 1.0 | 10.0108 s |
| Held out | One pass | 8 | 0 | 8 | 0.6667 | 7.4996 s |
| Held out | Full agent | 8 | 4 | 4 | 1.0 | 9.8227 s |

Conditional citation precision, citation coverage, and groundedness against
admitted evidence are 1.0 in every partition and variant. These are mechanical
scores on exact synthetic passages; they do not establish source truth. On the
small held-out denominators, dispute precision/recall and empty-corpus abstention
success were 1.0. Undefined denominators are `null` (N/A), never zero. Cost is
`null` because verified pricing was not configured.

## Paid Gemini results

The hard SQLite ledger reserved 26 of the authorized 30 calls: 23 HTTP 200,
two HTTP 429, and one unconfirmed request. The first seven HTTP 200 calls failed local response handling. A compressed-response wrapper defect was repaired and covered by a regression test; the original response bodies were not retained, so each failure cause remains unproven. The eighth request remained unconfirmed. Cases 9–20 then produced
12 usable one-shot responses. Cases 1–8 retain failed status and were not silently
replayed. The one-shot responses have no verified citations or source truth.

The two bounded Gemini full-agent probes ended `partial` (development case 1) and
`failed` (held-out case 13). Both had `fatal_error` stops, and the saved state
contains sanitized provider/structured-assessment errors. They are reported as
failed probes, not quality measurements. Four authorized calls remain unused.
The complete paid result is `.evidenceforge/evaluation/phase9_diverse/paid_results.json`.

## Verification and remaining gates

- Focused evaluation tests: 6 passed, including the 30-call guard and compressed
  HTTP response regression.
- Gemini and durable resume tests: 23 passed.
- Ruff and mypy checks for the edited evaluation modules passed.
- Independent review of every draft label remains required. Follow `REVIEW.md` and `ANNOTATION_PACKET.md`.
- Gemini full-agent results need a later provider-available benchmark with a
  fresh explicit budget; the current run is preserved without invented values.

This benchmark uses synthetic content, exact-string aspect matching, and very
small dispute/abstention denominators. Its metrics describe workflow behavior,
not general research accuracy. The original assignment PDF/rubric remains
unreconciled with the handoff, as noted in project progress.



## Follow-up audit — 3 October 2026

- Automated structural checks passed for all 20 draft labels; results are in
  `ANNOTATION_AUDIT.json`. This does not substitute for independent semantic review.
- The one-shot requests were matched to durable receipts by their exact request-body
  hashes. Twelve successful cases have 1,780 verified tokens in total. Eight cases
  have unknown usage. Historical per-case latency was not captured and remains N/A.
  The reconciliation is in `usage_reconciliation.json`; future runs record latency.
- The development Gemini workflow probe used five calls with 2,134 known input
  tokens and 345 known output/thinking tokens; one call has unknown usage. The
  held-out probe used one call with unknown usage. Paid results now record these
  counts; dollar cost is still N/A.
- The two Gemini probes used one subquestion, two passes and eight model calls per
  run. The fixture full-agent variant allowed three passes and 12 calls. These
  runs are therefore diagnostic probes, not matched quality comparisons.
- A scoring correction excludes uncited claims from the supported-citation
  numerator. Recomputing all 40 saved fixture rows produced identical metrics.
- The 30-call cap remains in force, with 26 reserved and four unused. A complete
  live comparison requires a separately authorized budget and a provider run
  without rate-limit failures.


## Extension readiness audit — 4 October 2026

The extension runner is now verified locally: its dry run opens the base ledger
read-only, a missing ledger cannot create a database, the original output path
is rejected before provider work, and the execution cap must fund the planned
maximum attempts. Paid ledger caps are immutable within an existing directory.
The manifest freezes relevant source files and the original paid-result hash.

Final relevant regression: **33 tests passed in 77.19 seconds**. Ruff passed and
mypy passed for all three evaluation modules. The dry run confirmed eight missing
one-shot cases, two full-agent cases and a maximum of 32 planned attempts. The
proposed 40-call extension has not executed: budget approval and independent
human review remain pending. See `EXTENSION_PLAN.md` and `ANNOTATION_PACKET.md`.
The original paid count remains 26 of 30; no new Gemini calls were made in this audit.

Only the retrieval-loop ablation has measured benchmark results. Contradiction,
ranking, and repair behavior have component tests but no separate Phase 9 ablation
measurements; no quantitative improvement is claimed for those components.
