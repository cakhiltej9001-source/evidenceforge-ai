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
The corrected comparison saved 40 Gemini answers using 136/140 approved calls,
all HTTP 200 and validated. The [AI review](../evaluation/V2_COMPARISON_REPORT_2026-10-06.md)
preserves complete-sentence/minimal-span quotation differences and planner scope drift
in workflow case 18. Both conflict workflows remain partial. Independent human
validation, general factual accuracy and source truth remain unclaimed.

Generated-plan guards reject added subannual requirements for annual/year requests
and respect explicit preferences. Date/season context authorizes relevant supporting
measurements without exempting finer unrequested breakdowns. Phrase matching limits
coverage; other entity, metric or population drift still needs plan review.
Numeric extraction also remains limited to explicit supported scopes and wording,
including electricity generation with "is", "totaled" and "totalled".

Retained public-source replay uses up to five integrity-checked WEB/API snapshots,
scripted reasoning and duplicate/missing/empty controls. Exact locators and citation
support measure mechanics in two energy-related retained corpora: EIA/Utility Dive
full text and Wikipedia search excerpts. [Nine checks passed](../evaluation/RETAINED_CORPORA_2026-10-08.md), including correctly partial status for absent wind evidence.
Independent semantic validation, source truth and live LLM quality remain open.

## Sources, documents and providers

The full research service can combine explicitly enabled Tavily search, the GB energy
API and selected documents. Mixed-source approval/edit/resume is verified with mocked
HTTP. Actual Tavily access/full pipeline/reconnect are verified with deterministic
reasoning; [measured scope](../TAVILY_VERIFICATION_2026-10-05.md) includes retained
boilerplate, so semantic research quality is still open. Default acquisition
remains synthetic or local-document retrieval. NESO percentages are GB half-hour shares, including
imports, not annual/global/absolute MWh output. API-derived prose is a deterministic
projection of validated JSON, not a quotation of provider-authored sentences.

TXT/PDF/DOCX ingestion is bounded. Optional local OCR requires Python 3.12 and
the `ocr` extra. Default child-process limits are five pages, four million pixels
per page, 120 seconds and 200 KB of text. Recognition can omit or misread text,
figures and tables. Quotations validate a labeled machine transcript; check wording,
numbers and layout against the original PDF image. DOCX row locators preserve cell
alignment; merged cells and visual layout still require inspection. Scope names
isolate stored content but do not authenticate users. Existing
Gemini mode sends selected question/evidence/context to Google. Availability and
rate limits can change; historical successes are not current availability guarantees.
Failed or uncertain paid calls are not retried automatically. Historical paid runs
without durable receipts cannot silently migrate; model/service instances are fresh
for each new run. Unknown usage and dollar cost remain N/A.

## Operation and deployment

This is a local trusted-user workbench. UI jobs run in a process executor.
A separate SQLite CLI queue persists fixture jobs for cooperating local workers;
each worker processes one job and exits. Plan approval and recovery after lease
expiry are explicit. Paid/live profiles are rejected. The CLI does not provide
hosted scheduling or distributed execution. Restart/deploy can interrupt UI work;
reconnect uses checkpoints and uncertain receipts block automatic repeated charges.
Graph version 8 checkpoints cannot silently resume older graph versions.

The explicit LangSmith probe uploads one synthetic counter span and requires exact
server readback. Standard configuration alone does not enable raw graph export.
Synthetic counter delivery and exact receipt readback passed on 8 October; see [verification](../LANGSMITH_VERIFICATION_2026-10-08.md). Full research payload tracing remains disabled.
These additions establish no new browser download check or independent human review.

Docker execution passed in the private repository's remote CI: image build,
nonroot UID, constrained research/reconnect, fresh-volume synthetic restore and
UI health. Official Render schema and local restart checks also passed. No
persistent Render instance or authenticated remote access path has been verified.
The local PC still lacks Docker. Render API/account access is [verified](../RENDER_ACCESS_VERIFICATION_2026-10-05.md).
The user selected free-only hosting (₹0/month), replacing the earlier ₹5 allowance.
Durable full-workbench storage stays local. The separate [public Streamlit fixture demo](../STREAMLIT_CLOUD.md) is live with
temporary session storage and no paid providers or document uploads. Authenticated Docker gateway checks passed in CI, including anonymous
browser/upload/media/WebSocket rejection and `RENDER=true` app login configuration.
Keep the complete local `.evidenceforge` directory for backup/recovery. Synthetic
restore verifies mechanics, not a future production backup of real user data.

## Optional future validation

| Work | Current boundary |
|---|---|
| Independent human review / real-source benchmark | Delegated AI review is complete; broader research validation is not established |
| Hosted operation | Public Streamlit fixture demo verified; durable full-workbench storage stays local under the free-only policy |
| Combined real Gemini/Tavily research-quality study | Tavily access and Gemini structured execution passed separately; synthetic results do not establish combined semantic quality |
| Separate grading/submission rules | The supplied PDF has no scored rubric, deadline or delivery format |

No missing credential, Gemini allowance or hosting decision blocks the selected
local deliverable. Original paid failures and ledgers remain preserved.

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
locally tested; a real Wikipedia fallback after simulated primary failure also
passed. Synthetic remote counter tracing is verified. Persistent hosted operation remains unverified; the
public offline Streamlit workflow has been deployed and exercised.
The PDF describes API-or-MCP extension and replaceable search providers; it does
not mandate a particular MCP server, hosting platform or human-reviewed benchmark.
