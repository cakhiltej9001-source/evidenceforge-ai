# Limitations and remaining decisions

## Evidence and reasoning

Reports retain and audit quotations. Matching a claim to a retained passage proves
that the snapshot supports the quoted text; it does not establish that the source
is correct. Lexical admission and fixture coverage are simple heuristics. Numeric
comparisons require explicit matching scopes, supported dates/units and grammar;
other semantic disagreements may remain unclassified. Ranking weights and source
families are inspectable heuristics, not calibrated trust probabilities.

The replay and fixture benchmark use synthetic content and scripted reasoning.
The repair replay deliberately injects one incorrect first draft. Its real audit
and bounded rewrite demonstrate control flow, not a measured hallucination rate.
The 20 evaluation labels remain draft; only the retrieval-loop ablation is measured.
The two incomplete Gemini probes do not provide a matched quality comparison.

## Sources, documents and providers

The full research service currently retrieves local documents or synthetic sources.
Dedicated NESO/Tavily acquisition adapters are separate; they do not provide general
live web research in the UI. NESO percentages are GB half-hour shares, including
imports, not annual/global/absolute MWh output. API-derived prose is a deterministic
projection of validated JSON, not a quotation of provider-authored sentences.

TXT/PDF/DOCX ingestion is bounded. Textless/scanned PDF pages disclose unavailable
OCR. Scope names isolate stored content but do not authenticate users. Existing
Gemini mode sends selected question/evidence/context to Google. Availability and
rate limits can change; historical successes are not current availability guarantees.
Failed or uncertain paid calls are not retried automatically. Historical paid runs
without durable receipts cannot silently migrate; model/service instances are fresh
for each new run. Unknown usage and dollar cost remain N/A.

## Operation and deployment

This is a local trusted-user workbench. UI jobs run in a process executor, not a
persistent distributed queue. Restart/deploy can interrupt active work; reconnect
uses checkpoints and uncertain receipts still block automatic repeated charges.
Graph version 8 checkpoints cannot silently resume older graph versions.

Docker and private Render configuration are prepared, and official schema/local
restart/synthetic backup-restore checks passed. No Docker runner, hosted instance,
authentication gateway or remote CI result has been verified. The current PC reports
about 4 GB RAM and disabled firmware virtualization; hosted container CI is the
proposed route. Real hosting requires an account/target and approved repository.
Local synthetic restore does not verify a future hosted production backup.

## Remaining external inputs

| Input | Why it is required |
|---|---|
| Completed independent 20-case annotation review | Needed before calling labels human-validated |
| Explicit additional Gemini allowance | Original evaluation cap is 30 with 26 reserved; the proposed extension needs up to 32 new attempts |
| Approved GitHub repository/CI execution | Needed to verify Docker on a compatible runner |
| Hosting account and access target | Needed for deployed runtime/storage/security checks |
| Original PDF and judging rubric | Needed for actual assignment/competition compliance |
| Deadline and submission format | Needed for final delivery/publishing decisions |

Proceeding to Phase 11 authorized these preparation materials. It did not approve
additional paid calls, a repository upload, a public deployment or a human review
claim. Those decisions remain open. No award/outperformance guarantee is made.
