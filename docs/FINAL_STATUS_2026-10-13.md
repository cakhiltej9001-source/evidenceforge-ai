# EvidenceForge status - 13 October 2026

Hosting remains **free only (INR 0/month)**. The Streamlit app now supports public live mode without a password
with private provider keys and temporary hosted storage. Durable full research stays local.

## Current fixes

New research runs use contract version 6. Earlier runs restore their saved
contracts; their reports and provider receipts are preserved.

- Line breaks, tabs or stray pipes alone cannot make flattened numeric rows safe.
  Ambiguous rows are excluded instead of having their columns guessed.
- Consistent pipe/tab tables retain their complete header and rows as one exact
  passage. Markdown exports show those passages as verbatim blocks, preserving
  line breaks and column delimiters. Oversized tables are rejected rather than
  split into rows without headers.
- Missing-data checks require the criterion's subject words in the same clause
  as an explicit absence statement. Unrelated absence statements and explicit
  negations do not establish completion.
- Numbered exercise blocks end at paragraph boundaries, so useful prose after
  the exercise is retained.
- Repair tests check unsupported claim text and qualifiers directly. A previous
  random evidence ID containing 999 caused a false failure; IDs are still shown
  unchanged and claim-safety assertions remain enforced.

These checks are conservative text rules. They do not reconstruct lost PDF
layout, handle every table format, prove full inventories, or establish general
semantic correctness.

## Verification

Final source commit: 969010c1da63871c2058bd0965cd81130314ca54.
[Full CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38335109168)
passed both jobs: **508 tests in 43.93 seconds**, Ruff lint/format, strict mypy,
package build, official Render schema validation, deployment smoke, constrained
Docker execution, persistence, backup/restore and authenticated gateway checks.

The initial quality update passed 507 tests and both Python/container jobs:
[measured CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38334666100).
Local focused verification passed 31 tests and strict mypy for 86 source files,
plus Ruff lint/format. The follow-up corrects the hash-dependent assertions and
adds another explicit negation case; all 22 focused follow-up tests passed.

The stricter policy was replayed against retained NASA evidence with networking
blocked. It rejected both problematic quotations and returned insufficient
evidence with three explicit gaps. The original state/report was byte-identical
and all provider ledger files were unchanged. Private results remain under
.evidenceforge/verification/report-quality-2026-10-13/.

No new provider requests were made while implementing the fixes. A subsequent
separately approved [live Gemini/Tavily check](LIVE_PROVIDER_CHECK_2026-10-13.md)
used 6 Gemini calls and 1 Tavily search: all provider calls passed. The report
correctly remained partial with two evidence gaps; fresh-process recovery
passed without extra calls. No new LangSmith request was made. The
[12 October provider verification](REMAINING_FIXES_2026-10-12.md) and
[earlier quality checks](REPORT_QUALITY_FIXES_2026-10-12.md) remain historical.
The corrected tests address
[the previous documentation pipeline failure](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38243292590)
without hiding the original result.

## Phase status

| Phase | Description | Status |
|---|---|---|
| 0 | Handoff and original assignment | Complete; 23 supplied PDF pages reconciled |
| 1 | Package, configuration, schemas and state | Implemented and tested |
| 2 | Manager, planning, context and queries | Implemented; plan scope still needs review |
| 3 | Retrieval, snapshots and provenance | Implemented; prior live Tavily and fallback checks verified |
| 4 | Coverage, synthesis, criticism and reports | Implemented; stricter table/absence guards verified offline and in a bounded live run; report partial; general semantic accuracy unclaimed |
| 5 | Documents, checkpoints and restart | Implemented locally; optional OCR bounded |
| 6 | Ranking, inspection and numeric comparison | Implemented for documented scopes and grammar |
| 7 | Budgets, receipts, cancellation and tracing | Implemented; synthetic LangSmith delivery/readback verified on 12 October |
| 8 | UI, approvals and exports | Implemented; prior hosted fixture downloads and visitor isolation verified |
| 9 | Evaluation and Gemini comparison | Controlled comparison and AI review complete; independent human review open |
| 10 | API, containers and deployment | Local durability and Docker CI verified; public fixture demo deployed; durable hosted operation deferred |
| 11 | Setup and submission materials | Prepared; external acceptance unclaimed |

## Remaining external or optional work

- Independent human benchmark review and independent OCR accuracy review.
- Broader real-source accuracy evaluation and more general table/semantic support.
- Hosted durable storage and background jobs, deferred under free-only hosting.

No new hosting resources were created. Credentials and private replay evidence
remain ignored by Git. See [setup](submission/SETUP.md),
[limitations](submission/LIMITATIONS.md), and the
[12 October historical status](FINAL_STATUS_2026-10-12.md).

## Fresh live test with screenshot

A second separately approved campaign used six Gemini calls and one Tavily
search. See the [measured outcome and browser screenshot](LIVE_PROVIDER_SCREENSHOT_2026-10-13.md).
Earlier verification records and provider receipts remain preserved.

## Hosted live-mode update

The owner requested live access behind login and reported saving private secrets.
See [implementation and checks](STREAMLIT_LIVE_2026-10-13.md). Configured local UI
research also defaults to Gemini and Tavily. After publishing and rebooting, the owner confirmed the new sign-in screen.
Independent anonymous browser activation remains unconfirmed; the earlier
anonymous fixture results remain historical. No hosted API calls were submitted.

## Password removed at owner request

See [public live mode](STREAMLIT_PUBLIC_LIVE_2026-10-13.md). Visitor scopes replace
the shared owner workspace for anonymous sessions; provider keys remain private.
Per-run API limits remain in force. Hosted activation is checked separately.

## Hosted setup verified - 14 October 2026

The missing root-level API keys were saved. An independent anonymous browser
verified all six live UI checks: password absent, Gemini and Tavily selected,
Create plan available, caller scope absent and no setup error. See the
[actual hosted screenshot](HOSTED_LIVE_READY_2026-10-14.md). No research or new
provider calls were requested by this check. Hosting remains free with
temporary storage; earlier pending deployment/setup statements are superseded.

## Three hosted live cases - 14 October 2026

The separately approved 18-Gemini/3-search campaign used 13 Gemini calls and two
Tavily searches. Photovoltaics completed, seasons ended partial after a model-stage
failure, and the atmosphere case failed before retrieval. See the
[screenshots, usage receipts and limitations](HOSTED_LIVE_TESTS_2026-10-14.md).
Two model-stage failures and incomplete detailed-error exports remain open;
general live reliability is not established. Hosting remains free only.

## Rose response recovery - evidence updated 15 October 2026

A separately approved campaign used three Gemini calls and one Tavily search.
The hosted first stage timed out. New combined review/planning passed locally,
then query generation returned HTTP 503. The existing source-only recovery control
completed a real Tavily run with 33 exact-quotation audits and no Gemini generation.
See [measured outcomes and screenshots](ROSE_RECOVERY_2026-10-14.md).
The repaired source passed 540 tests and both CI jobs. Full Gemini workflow success
and activation of the second hosted repair remain unconfirmed. No extra provider
calls are being made; hosting remains free only.
Safe detailed-error exports are now implemented and covered by regression tests;
the earlier note listing their omission describes the preceding hosted campaign.
