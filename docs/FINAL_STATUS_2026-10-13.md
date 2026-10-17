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

## Fresh full live workflow passed - 15 October 2026

The [fresh live rose workflow](LIVE_ROSE_SUCCESS_2026-10-15.md) completed locally
with all five Gemini stages successful, one Tavily search, 32 retained passages,
six exactly supported citations and zero tool errors. Saved planning was reused;
the continuation used four model calls and one search. Total known tokens for
this run were 55,606. No automatic retries occurred.
Together with the preceding campaign, eight approved Gemini calls and two approved
searches are now exhausted. Earlier unrelated allowances remain separate.
This verifies the current combined workflow for one local live case. Public
Streamlit still showed the older planning path in a zero-call preflight, so its
latest-build activation remains unconfirmed. Hosting remains free only.

## Explicit source selection fixed - 15 October 2026

The [source-selection repair](SOURCE_SELECTION_FIX_2026-10-15.md) blocks real
research with no selected source before any API call. Synthetic demonstrations
now require an explicit mode choice and use offline reasoning. Full source CI
passed 544 tests and both jobs for commit 4983c5e; 22 unique focused tests passed.
No Gemini, Tavily or LangSmith calls ran for this repair. The public preflight
still saw the older build. The browser management tool timed out, and an owner
reboot was requested; hosted activation is not yet confirmed. Hosting remains free only.

## Hosted activation verified after reboot - 15 October 2026

The owner rebooted the app. A fresh anonymous browser verified version 2026-10-15.1,
the combined-planning guidance and explicit research mode. A source-free submission
was blocked without creating a plan or report and with zero Gemini/Tavily calls.
The [hosted screenshot and measured result](SOURCE_SELECTION_FIX_2026-10-15.md#hosted-verification-after-owner-reboot)
close the hosted activation item above. Full paid workflow success remains the
separately recorded local live test. Hosting remains free only.

## Saved access for blocked source links - 16 October 2026

The [blocked-source repair](BLOCKED_SOURCE_FIX_2026-10-16.md) adds local saved-passage links and exact-text downloads while preserving original URLs. The publisher returned 403 for both host variants; the app cannot remove that external restriction. Only report-cited evidence from the existing scoped state is shown, with excerpt/full-page limitations.
Source commit 669d3fe passed 547 tests and both CI jobs; 34 focused regressions passed locally. No new Gemini or Tavily calls ran. Hosted version 2026-10-16.1 still needs activation: the browser management tool timed out and an owner reboot was requested. Hosting remains free only.

## Hosted saved-source access verified after reboot - 16 October 2026

The owner rebooted the app. A fresh anonymous browser verified version 2026-10-16.1,
local source links, retained-passage viewing and plain-text download with original
URL metadata. The test explicitly used the offline synthetic demonstration with
live-source controls absent: zero Gemini calls and zero Tavily searches.
The [actual hosted screenshot and result](BLOCKED_SOURCE_FIX_2026-10-16.md#hosted-verification-after-reboot)
close the activation/download item above. The publisher can still return 403;
the app provides saved excerpts rather than bypassing that restriction or claiming
a complete article. Full source CI remains 547 passing tests. Hosting remains free only.

## Answer before key findings implemented - 16 October 2026

The [answer-first presentation](ANSWER_FIRST_2026-10-16.md) adds short exact cited excerpts before Key Findings in the workbench and its Markdown download. Relevant unresolved differences prevent a single winner, qualifiers remain attached, and canonical claims/evidence are preserved. Existing compatible saved reports can use the view without new provider calls.
Source commit 11e6f4c passed 554 tests and both CI jobs, with 89 source files type-checked. Local focused runs covered 41 unique tests. No new Gemini or Tavily calls ran. Version 2026-10-16.2 still needs hosted activation: the management connection timed out and an owner reboot was requested. Hosting remains free only.

## Hosted Answer-first layout verified after reboot - 16 October 2026

The owner rebooted the app. A fresh anonymous browser verified version
2026-10-16.2, Answer before Key Findings, and matching order and cited answer text
in the actual Markdown download. Saved-source links and text downloads also passed.
The check explicitly selected offline synthetic demonstration with live-source
controls absent: zero Gemini calls and zero Tavily searches. Its partial-answer
label remained visible. The [hosted screenshot and measured result](ANSWER_FIRST_2026-10-16.md#hosted-verification-after-reboot)
close the preceding activation item. Full source CI remains 554 passing tests;
this presentation check does not claim a fresh hosted live-provider research run.
Hosting remains free only.

## Energy API option removed - 17 October 2026

The workbench no longer offers the GB half-hour energy API checkbox or its
help text. New form submissions use Tavily and/or imported documents, with the
energy source disabled. Source commit b9dddd5 passed all four existing source-
selection UI tests, lint/format and [full GitHub CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38994699249).
The public read-only check did not yet observe version 2026-10-17.1; hosted
activation remains pending. No Gemini calls or Tavily searches were made.

## Empty question box and writing guidance - 17 October 2026

The research question now starts empty in local, hosted and synthetic forms.
A taller input has a placeholder inviting the user's own question, a short
explanation/comparison/document prompt line, and a focus tip. Blank or whitespace-
only submissions show a clear message before any research starts.
All seven existing focused UI checks passed in 98.63 seconds, including typed
questions, zero-call blank submission, approval/downloads and visitor isolation.
Lint and formatting passed. No Gemini or Tavily calls ran. The published build
marker is 2026-10-17.2; hosted activation is checked separately.

## Partial-report answer and usage repair - 17 October 2026

The [report recovery](REPORT_RECOVERY_2026-10-17.md) addresses missing how-to
answers despite retained evidence, visible unresolved requirements, entity display,
and conflicting token summaries. UI and export totals use scoped durable Gemini
receipts. New policy 3 improves practical planning and source/quote guidance; old
saved runs preserve their original request hashes and replay behavior. Call/search
limits and the no-automatic-paid-retry policy remain unchanged.
Forty unique focused checks passed across the initial 38-case run and final
14-case recovery suite. Direct strict typing, project lint and format checks passed.
No new live Gemini or Tavily calls ran. Version 2026-10-17.3 still needs hosted
activation verification; the browser management connection timed out.
