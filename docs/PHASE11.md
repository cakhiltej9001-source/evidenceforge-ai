# Phase 11 — submission and demonstration

Prepared on 4 October 2026 (Asia/Calcutta), following the user's instruction to continue to the next phase.

## Delivered

- README with a reproducible offline start, provider/source distinctions and measured results.
- [Architecture](submission/ARCHITECTURE.md): implemented graph, storage and service boundaries.
- [Setup guide](submission/SETUP.md): installation, offline UI, approvals, provider configuration and persistence checks.
- [Demo script](submission/DEMO.md): a 4 minute 30 second walkthrough.
- [Requirements checklist](submission/REQUIREMENTS.md): B01–B13/P01–P06 implementation evidence and qualifications.
- [Evaluation table](submission/EVALUATION.md): measured fixture results and incomplete Gemini comparison.
- [Limitations](submission/LIMITATIONS.md): outstanding validation and operational constraints.
- `scripts/prepare_demo.py`: fresh service runs and clickable local report/evidence replay.

## Executed demo verification

All four scenarios used offline synthetic fixtures, with zero search or model provider calls. The repair scenario deliberately supplies an unsupported first draft; production citation checking and rewrite routing then repair it. This demonstrates workflow mechanics, not a measured model hallucination rate.

| Scenario | Outcome | Retrieval passes | Rewrites | Retained claims |
|---|---|---:|---:|---:|
| Coverage loop | completed / sufficient | 2 | 0 | 2 |
| Dispute | partial / no_progress | 2 | 0 | 5 |
| Audit repair | completed / sufficient | 1 | 1 | 2 |
| Graceful partial | partial / pass_limit | 1 | 0 | 1 |

Captured manifest: `.evidenceforge/demo/phase11/manifest.json`. Each scenario retains report, state, audit and support graph exports. Clicking a finding reveals its source, exact passage and locator. The repair replay also records the injected and corrected drafts.

Reproduce from the project directory:

```powershell
uv run --locked python scripts/prepare_demo.py
uv run --locked python -m http.server 8503 --bind 127.0.0.1 --directory .evidenceforge/demo/phase11
```

Open `http://127.0.0.1:8503/`. Serve this demo directory only. Generated replay and local research data remain ignored by Git.

## Final checks

- Full regression: **349 passed in 694.19 seconds**.
- Ruff lint: all checks passed.
- Ruff formatting: 124 files already formatted.
- Strict mypy: no issues in 71 source files.
- Wheel and source distribution build passed.
- Checked 53 local documentation/replay links: zero missing; all four saved replay states verified.

## Completion and remaining gates

Phase 11's local submission materials and demonstration are prepared. The original
23-page PDF has now been read and reconciled in
[ORIGINAL_PDF_RECONCILIATION.md](submission/ORIGINAL_PDF_RECONCILIATION.md).
The source-document gate is closed. Baseline live-source/report/deduplication gaps
remain; overall assignment acceptance is unclaimed. The PDF has no grading rubric
or submission deadline.

Following the user's delegation, all eight missing Gemini one-shots were recovered,
for 20/20 usable cases. The extension plus repair diagnostics used 28/40 authorized
additional calls; the original ledger remains 26/30. The repaired fresh workflow
returned two cited claims, partial at three passes, with all nine calls succeeding.
[Detailed results](evaluation/EXTENSION_REPORT.md) retain earlier failures and separate
post-repair diagnostics. All 20 labels have an [AI review](evaluation/AI_REVIEW.md);
human validation and a defensible research-quality comparison remain unclaimed.

The [private GitHub repository](https://github.com/cakhiltej9001-source/evidenceforge-ai) exists and [remote CI passed](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37169054208) on
`ab66cb464d4b3d024f394ccb3cdc3e5e67746ff8`. Docker build, nonroot execution,
constrained research/reconnect, synthetic backup/restore and health passed.
The provider repair also passed 24 affected offline tests, lint/format and strict
types locally; CI repeats all checks on new pushes. Local Docker remains absent.

Persistent hosting still needs an account/target, access path and spending cap.
Live Tavily needs configured access. Original-PDF reconciliation is complete;
remaining implementation differences are recorded in the verified checklist.
No Render deployment or OS installation was performed.

- Both distribution archives inspected (221 entries): no configured credentials, private runtime directories or local databases. Local demo HTTP 200 and synthetic label verified.

## Supplied original and latest source checks

The PDF's page-13 format adds a 2-3 paragraph summary and per-source evidence chunks;
current Markdown uses quoted bullets and separate inspection/state evidence exports.
The PDF's same-pipeline live web/external requirement is not fulfilled by standalone
acquisition commands. The requirements checklist now records these as partial.
The current runtime revision `93b320d65d87dd449905ddc65d91315ef0bf3303` passed
350 tests (14.68 s), lint/format, strict types and both remote CI jobs:
https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37170191649 .
This reconciliation changes documentation only and makes no provider calls.

## Original assignment runtime fixes — 5 October 2026

The 23-page PDF is mapped and its identified runtime gaps have been addressed with
explicit mixed-source research controls, supported summary paragraphs, per-source
chunk lists and conservative literal working-set deduplication. Prior source records
and citation audits remain authoritative. See the
[implementation record](ASSIGNMENT_FIXES_2026-10-05.md) and updated
[requirements](submission/REQUIREMENTS.md) for tested scope and remaining inputs.
Actual live Tavily and persistent hosting are still unverified; P02–P05 production
guidance and broader research-quality validation remain qualified. Earlier counts
and baseline-gap statements are historical, not additional passing measurements.

## Completed verification — 5 October 2026

[CI run 37253453020](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37253453020)
passed both jobs on source `36d1e44a414bbc9ced7a74fa151b30faffd53593`.
Completed **07:28:22 IST** (01:58:22 UTC):

- **362 tests passed**, 17.90 seconds, Linux/Python 3.12.
- Ruff lint passed; 137 Python files formatted; strict mypy passed, 72 source files.
- Wheel/sdist built; official Render schema and offline deployment smoke passed.
- Docker build, UID 10001, 512 MB/half-CPU research and fresh-container reconnect,
  fresh-volume synthetic backup/restore, and UI health all passed.
- Private repository visibility reconfirmed; 157 allowlisted source files passed
  configured-credential/private-runtime-path checks; 59 local documentation links
  passed. Local paid ledgers and Gemini adapter provenance remained unchanged.

At **07:29:33 IST**, refreshed four provider-free local replay runs. Coverage-loop
completed in two passes; numeric dispute remained partial/no-progress; injected
unsupported draft was repaired once and completed; pass-limited result remained
partial with its gap. Source chunks/paragraph summaries were inspected in the new
saved report. Artifacts remain in ignored `.evidenceforge/demo/phase11/`.

The original PDF/page mapping and the identified baseline engineering mechanics
are addressed within the conservative limits above. Actual Tavily access, persistent
hosting, independent research-quality validation and P02–P05 production guidance
remain open. No new real model/search/API request ran for these fixes.
