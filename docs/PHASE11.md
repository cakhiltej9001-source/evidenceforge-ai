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

Phase 11's local submission materials and demonstration are prepared. Assignment acceptance remains unverified because the original PDF, rubric and deadline have not been supplied.

Phase 9 independent annotation review and a successful matched Gemini comparison remain open. The paid ledger remains 26/30; no new Gemini calls were made for this phase. Additional budget authorization is still required for the proposed extension.

Phase 10 local source/runtime checks passed. Docker image/runtime checks and hosted deployment checks remain open. This computer has about 4 GB RAM and reports firmware virtualization disabled. Creating/uploading a private GitHub repository for hosted CI and provisioning a hosting target still require the user's pending decisions.

No repository publication, external deployment or OS installation was performed. Passing offline tests does not close these external gates.

- Both distribution archives inspected (221 entries): no configured credentials, private runtime directories or local databases. Local demo HTTP 200 and synthetic label verified.
