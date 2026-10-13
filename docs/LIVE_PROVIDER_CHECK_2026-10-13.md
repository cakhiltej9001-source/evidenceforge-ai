# Live Gemini and Tavily verification - 13 October 2026

A new, separately approved allowance was used for one local NASA atmosphere
comparison with contract version 6. Earlier campaign allowances and receipts
were preserved.

## Provider results

| Item | Measured result |
|---|---|
| Model | gemini-3.1-flash-lite |
| Gemini calls | 6 of 6 approved; all six roles succeeded |
| Gemini tokens | 12,365 total, including reported thinking tokens |
| Tavily | 1 of 1 approved search; HTTP 200 |
| Tavily usage | 1 search credit; 29,477 response bytes |
| Sources | 3 NASA sources, 5 retained evidence passages |
| Report | Partial; pass_limit after the one approved retrieval pass |
| Accepted findings | 1 exact retained quotation with supported citation |
| Remaining gaps | Earth composition evidence and missing-percentage inventory |
| Provider errors | None |
| Extra calls on reconnect | 0 |
| Hosting | Free only; no hosting changes |

The six successful roles were input guardrail, planner, query generator,
coverage evaluator, synthesis and critic. Automatic paid retries were disabled.
A durable campaign ledger enforced the six-call cap; an exclusive Tavily receipt
enforced one search. Estimated USD cost was unavailable and is not reported as
zero.

## Quality and recovery checks

All eight live-run checks passed: successful roles, exact evidence offsets,
supported nonempty claims, unique claim text, nonempty findings, saved Markdown
and JSON exports, terminal resume without calls, and unchanged historical ledgers.

All nine fresh-process checks passed with networking forbidden: honest terminal
status, one citation audit per claim, supported audits, exact retained quotations,
exact evidence offsets, no duplicate findings, identical restored state, no
network attempts and unchanged paid receipts.

The accepted quotation concerns Mars atmospheric composition and preserves the
source's location and season context. It is not presented as a complete Earth/Mars
comparison. The report explicitly flags the two unmet criteria even though the
model critic approved the draft. No flattened table or worksheet exercise was
used as a final claim.

This is one bounded integration check, not broader research-quality validation.
Independent human review remains open.

## Private artifacts

Campaign: .evidenceforge/verification/gemini-tavily-2026-10-13/
Run: run_1d99937322d3403c82f66193c24a356e

Authorization, call ledgers, snapshots, report exports, result.json and
offline_review.json remain private and ignored by Git. No credentials or private
source payloads are included in this document.
