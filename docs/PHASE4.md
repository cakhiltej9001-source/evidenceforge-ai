# Phase 4: bounded research and cited reports

Implemented 1 October 2026. This milestone is an offline workflow demonstration with structured
synthetic fixtures. It does not answer the solar/wind question using actual electricity measurements.
No live model or external search was run.

## Run in PowerShell

```powershell
cd "C:\Users\AKHILTEJ\Documents\ChatGPT\AI Research agent"
uv run --locked evidenceforge-research "Compare solar and wind electricity output."
uv run --locked evidenceforge-research "Compare solar and wind electricity output." --demo second-pass
uv run --locked evidenceforge-research "Compare solar and wind electricity output." --demo empty
```

Default `immediate` completes in one retrieval pass. `second-pass` supplies solar evidence in pass 1
and wind evidence in pass 2; retained acquisitions and query history prove that another retrieval
batch actually ran. `empty` returns an insufficient-evidence report with unmet criteria.
The command prints Markdown and absolute saved paths. `--data-dir` changes the local storage root.
The previous `evidenceforge-retrieve` command still demonstrates one unfinished retrieval pass.

Reports are saved under `.evidenceforge/reports/<run_id>/report.md`, alongside `state.json`.
Each file is written atomically. The pair is not a database transaction; an I/O failure can leave one
file saved, raises an error and prevents a successful delivery confirmation. Generated files are ignored
by Git. Saved JSON is an inspection artifact, not a resumable LangGraph checkpoint.

## Routing

Manager starts Planner and Context Manager in parallel; their all-predecessor join runs Query Generator.
Queries lead to Source Processor, Evidence Extractor and Coverage Evaluator. Coverage emits a record
for every question, unmet acceptance criteria and targeted follow-up queries. Research continues only
while the pass, search, evidence, elapsed-time and fixture-assessment allowances permit it.
An empty set of new queries stops without incrementing the completed-pass count.
Unchanged coverage is bounded by a no-progress counter and the overall pass limit.

Evidence proceeds through Synthesis, Critic and Citation Checker before Finalizer. Critic revisions
and citation repairs both reserve one unit from the same `revision_count`/`max_rewrites` allowance.
Every rewritten draft gets fresh criticism and fresh citation checks; stale approvals are cleared.
The graph recursion limit is a final backstop, with an explicit terminal stop reason.

`iteration_count` counts completed retrieval batches. `quality_attempts` counts coverage, synthesis
and critic fixture invocations, including expected failures. These attempts use `max_model_calls` as a
local ceiling and preserve quality capacity before another coverage pass. Planning/query fixtures are
counted separately on their adapter. These are not measured paid model calls, tokens or dollar usage.
Live provider accounting and consolidated guardrails remain later milestones. Search reservations and
receipts retain the Phase 3 implementation. Unknown real usage/cost remains unknown.

## Support and rendering

Coverage fixtures match criterion tokens against retained passages. This is a lexical heuristic.
Synthesis returns structured claim/question/evidence references before any Markdown is created.
Unknown references, malformed outputs and invalid coverage indices produce sanitized typed errors.

The citation checker conservatively requires an exact full retained passage quotation for every claim,
including inferences and recommendations. It checks question association, citation IDs, qualifier text,
snapshot hash and exact source offsets. It accepts no free paraphrase, date/unit/numeric change or
uncited assertion. This verifies quotation provenance, not whether a publisher's claim is true.
Semantic support, contradiction analysis and real model integrations remain future work.

The finalizer retains only audited supported claims. Unsupported claims are omitted and their blocking
audits remain in `unresolved_audits`; partial output discloses omitted claims, unmet criteria, critic
objections, errors and the stop reason. Every report has Summary, Key Findings and Sources. Source
names and quoted passages are escaped; links come from retained source records, not draft prose.
Completed status requires sufficient fixture coverage, critic approval and supported claims.

## Verification

Behavioral tests cover immediate sufficiency, genuine second-pass acquisition, no evidence,
unsupported-claim repair, critic and citation shared exhaustion, malformed/unknown references,
partial reports at pass limits, recursion backstop, quality capacity, missing qualifiers, uncited
nonfact claims, corrupted snapshots and failed output writes. The existing Phase 1–3 suite remains
part of the regression gate. Exact final results are recorded in PROGRESS.md.

## Next milestone

Phase 5: PDF/DOCX/TXT ingestion, located chunks, scoped lexical retrieval, workflow SQLite
checkpoints and a separate prior-report repository. Original assignment PDF reconciliation is still
pending. Phase 5 has not started.