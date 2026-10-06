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
The 20 evaluation labels have a documented Codex AI review; independent human
validation is not claimed. The corrected offline v2 comparison has 40 saved rows
and zero provider calls. The approved paid comparison did not start because the
environment approval service rejected the network command after exhausting its
review credits. Broader synthetic questions and short dependency corpora do not
establish source truth or a matched research-quality comparison.

## Sources, documents and providers

The full research service can combine explicitly enabled Tavily search, the GB energy
API and selected documents. Mixed-source approval/edit/resume is verified with mocked
HTTP. Actual Tavily access/full pipeline/reconnect are verified with deterministic
reasoning; [measured scope](../TAVILY_VERIFICATION_2026-10-05.md) includes retained
boilerplate, so semantic research quality is still open. Default acquisition
remains synthetic or local-document retrieval. NESO percentages are GB half-hour shares, including
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

Docker execution passed in the private repository's remote CI: image build,
nonroot UID, constrained research/reconnect, fresh-volume synthetic restore and
UI health. Official Render schema and local restart checks also passed. No
persistent Render instance or authenticated remote access path has been verified.
The local PC still lacks Docker. Render API/account access is [verified](../RENDER_ACCESS_VERIFICATION_2026-10-05.md).
Actual hosting still requires repository access verification, a deployment/access
choice and an approved spending cap. Synthetic restore does not verify a future production backup.

## Remaining external inputs

| Input | Why it is required |
|---|---|
| Benchmark corrections and semantic comparison | Corrected v2 questions and offline protocol are complete; the approved paid run was blocked before execution by the environment approval-credit limit. Independent human validation is not claimed |
| Hosting deployment/access choice and spending cap | Render API access verified; repository connection and actual persistent runtime/storage/security checks remain pending |
| Tavily | Credential/acquisition/full pipeline gate closed; combined real Gemini/Tavily semantic research quality remains unverified |
| Any separate grading/submission brief, if one exists | The reviewed original PDF provides no rubric, deadline or delivery format |
| Deadline and submission format | Needed for final delivery/publishing decisions |

Subsequent user delegation authorized 40 additional Gemini calls and the private
repository/upload/CI; these actions executed, with 28 additional calls reserved.
Codex reviewed all 20 labels as AI without supplying a human attestation. Persistent
hosting remains pending. Tavily configuration and a bounded live full pipeline check are complete. No award or provider
outperformance is established by these checks.

## Verified original-PDF differences

The original 23-page PDF is supplied and fully reconciled in
[ORIGINAL_PDF_RECONCILIATION.md](ORIGINAL_PDF_RECONCILIATION.md). The missing-file gate
is closed. Full research now accepts explicit live source choices with documents, and
reports contain supported summary paragraphs and per-source evidence chunks. Literal
cross-source copies/contained passages are grouped for model input while original spans
remain retained. Nonidentical partial overlaps and paraphrases are kept separate to
preserve distinct facts and qualifiers; semantic deduplication is not established.
If fewer than two supported summary claims exist, a shorter summary is disclosed.
Production guidance now includes semantic input classification, ordered search
fallback, lowest-score evidence eviction and bounded local tracing. These are
locally tested; remote provider diversity, remote tracing and hosted operation
remain unverified.
The PDF describes API-or-MCP extension and replaceable search providers; it does
not mandate a particular MCP server, hosting platform or human-reviewed benchmark.
