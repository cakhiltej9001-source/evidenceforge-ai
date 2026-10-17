# Review budget repair - 17 October 2026

## Reported failure

The supplied AI-engineering report retained 40 passages and passed all 11 exact
citation audits. Coverage assessed five of five criteria as supported. Report
review failed with a generic provider error. The export had five workflow stages,
four provider receipts, one unknown usage record and no failed provider receipt.

An offline reconstruction identified a request that would exceed the default
100,000-token hosted allowance. The export omits its original configured budget
and precise local rejection reason, so this is a reconstructed diagnosis.

## Repair

New local and hosted workbench runs use production policy 4. Review receives:

- The original research request and approved questions/criteria.
- Complete evidence referenced by claims and coverage assessments.
- Both sides of retained numeric contradictions.
- Every referenced provenance record, including duplicate occurrences.

The complete evidence store, raw quotations and citation audit remain available.
Saved policies keep their original request bodies and paid-response replay.
A fresh recovery run can use policy 4; a terminal historical report is not rewritten.

Local token/call reservation failures have a distinct exception and budget
category. They produce a token/call-limit stop reason and a public timeline label.
Usage reports separately count requests blocked locally. These known unsent
attempts are not added to unknown provider usage; unexplained missing receipts
and uncertain/failed paid outcomes remain conservative.

## Measured offline reconstruction

| Measurement | Previous review | Repaired review |
| --- | ---: | ---: |
| Retained passages | 40 | 40 |
| Claims | 11 | 11 |
| Evidence records sent for review | 39 | 14 |
| Next-request conservative token reservation | 68,534 | 36,248 |
| Recorded previous tokens | 43,757 | 43,757 |
| Combined required allowance | 112,291 | 80,005 |
| Fits default 100,000-token cap | No | Yes |

These reservation numbers are upper bounds used by the application, not billed
token totals. The repaired request was reconstructed from the supplied export;
no provider was contacted and no new answer was generated.

## Verification and deployment

The focused regression module passed **13 tests in 51.96 seconds**, including
complete reference retention, numeric counter-evidence, known local blocks,
uncertain usage, failed reservations and historical paid critic-response replay.
Local typing passed across 89 source files. Lint and formatting passed.
[Full source CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/39036637322) passed **583 tests in 50.59 seconds** on source commit 65f4f04. Both CI jobs passed, including typing, lint/formatting, package build, checkpoint smoke, container persistence, backup/restore and gateway checks.

The deployment marker is **App version: 2026-10-17.5**.
Call/search/token caps are unchanged. No automatic paid retry was added.
No new Gemini, Tavily or LangSmith requests ran during this repair.
Hosting remains free only.

[Sanitized reconstruction counters](REVIEW_BUDGET_FIX_2026-10-17.json)

This verifies local behavior and request sizing. A fresh live provider response
has not been verified for this build. Larger or more complex reports can still
reach their configured limit; they should now receive an accurate explanation.

After the owner rebooted the app, a fresh read-only browser check observed **App version: 2026-10-17.5** on **18 October 2026**. Hosted activation is verified. This check made zero Gemini calls and zero Tavily searches. Create a new plan to exercise policy 4. Existing terminal reports retain their original status. A fresh live provider response has not been verified for this build.
