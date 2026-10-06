# Requirements and submission checklist

The initial audit reconciled all 23 supplied original-PDF pages against source
revision `93b320d65d87dd449905ddc65d91315ef0bf3303`. The 5 October implementation
update below supersedes that snapshot's live-source/report/deduplication gaps.
[Original-PDF reconciliation](ORIGINAL_PDF_RECONCILIATION.md) records verified pages,
source hash, interpretations and concrete gaps. The PDF contains no scored rubric
or deadline. Baseline mechanics are implemented conservatively; actual Tavily access
and full research are [verified with deterministic reasoning](../TAVILY_VERIFICATION_2026-10-05.md).
Research-quality validation remains open. Paths below are
relative to `src/evidenceforge/` unless marked otherwise.

## Baseline traceability

| ID | Requirement | Implementation/evidence | Status and qualification |
|---|---|---|---|
| B01 | Focused subquestions and criteria | `nodes/planner.py`, `schemas.py`; `tests/test_planning.py` | Implemented and locally tested |
| B02 | Web/document/external source paths (PDF 2, 5-6, 10) | `retrieval/tavily.py`, `retrieval/documents.py`, `retrieval/carbon_intensity.py`, `services/research.py` | Implemented explicit mixed-source full graph, CLI/UI flags, approval/edit/reconnect and HTTP cleanup; mocked web/API/document integration verified. Actual Tavily acquisition/full research/reconnect verified on 5 October with one search and deterministic reasoning; semantic quality remains open. No particular MCP server is mandated |
| B03 | Manager coordinates planning/context | `graph/research.py`, `nodes/manager.py`, `nodes/context.py`; planning tests | Implemented all-predecessor join; one downstream initialization |
| B04 | Source-specific bounded queries | `nodes/queries.py`; `tests/test_planning_queries.py` | Implemented, including follow-up queries |
| B05 | Exact evidence, duplicates and provenance (PDF 10-11) | `nodes/sources.py`, `nodes/extraction.py`, `storage/artifacts.py`, `evidence/deduplication.py`, `evidence/ranking.py` | Implemented exact spans and conservative cross-source working-set deduplication; all original source/acquisition/locator records retained. Only literal copies/full containment with represented question links collapse; distinct wording/partial overlaps remain. Lexical relevance is not truth verification |
| B06 | Shared state and replay-safe reducers | `graph/state.py`, `graph/reducers.py`; `tests/test_state.py` | Implemented contracts, cross-references and bounded records |
| B07 | Coverage gaps trigger another pass | `nodes/quality.py`, `graph/research.py`; `test_second_pass_adds_new_evidence` | Verified synthetic two-pass demo |
| B08 | Bounded stop with disclosed gaps | `nodes/quality.py`, `reporting.py`; `test_pass_limit_returns_partial_with_gaps` | Verified partial/pass-limit path and other stop conditions |
| B09 | Required report sections and sources (PDF 13) | `reporting.py`, `exports.py`; research/Phase 8 tests | Implemented 2-3 audited summary paragraphs when enough supported claims exist, plus per-source evidence chunks/locators. A shorter summary is explicitly disclosed when support is insufficient |
| B10 | Critic and shared revision budget | `nodes/quality.py`; critic/citation allowance tests | Implemented; exhausted repairs cannot manufacture completion |
| B11 | Trace claims to evidence | `nodes/quality.py`, `evidence/projection.py`; audit/support tests | Exact quotations and snapshot integrity verified; independent source truth/semantic accuracy not established |
| B12 | Registered compiled LangGraph | `graph/research.py`, `graph/builder.py`; planning/research tests | Implemented and executed |
| B13 | SQLite thread checkpoints and restart | `storage/checkpoints.py`, `services/research.py`; persistence/Phase 8 tests | Local process restart and scoped reconnect verified; hosted durability unverified |
| P01 | Secrets/environment configuration | `config.py`; config tests and Git/Docker excludes | Keys private/redacted; optional provider requests require explicit configuration |
| P02 | Input validation/clarification (PDF 19) | `nodes/input_review.py`, `tests/test_production_controls.py` | Implemented for production Gemini runs: semantic categories, bounded guidance and pre-manager rejection; fixture/library legacy paths remain unchanged |
| P03 | Progress, usage and traces (PDF 20) | `services/node_trace.py`, model-call ledger and `tests/test_production_controls.py` | Local bounded metadata tracing and durable usage/receipts implemented; payload capture is opt-in and remote tracing remains unverified |
| P04 | Typed errors and ordered search fallback (PDF 21) | `retrieval/fallback.py`, `retrieval/wikipedia.py`, `nodes/sources.py` | Implemented as an ordered provider chain with per-provider budget receipts and provenance; live secondary-provider operation still needs hosted/live verification |
| P05 | Bounded evidence and prior context (PDF 21) | `evidence/retention.py`, `nodes/extraction.py`, `storage/local_context.py` | Implemented lowest-score eviction with pinned-claim protection and immutable source/acquisition retention; quality remains heuristic |
| P06 | Phase-specific read-only tools | Model/retrieval contracts and service dependency injection | No arbitrary write/code-execution tool offered to research models |

## Additional implemented features

| Feature | Evidence | Limit |
|---|---|---|
| Plan approval/editing | Phase 8 tests, local deployment smoke | Owner IDs are not authentication |
| Claim graph and selected support | `evidence/projection.py`, UI, Phase 11 replay | Projection of retained records; no independent truth score |
| Dispute/unit/date/source-family handling | Evidence intelligence tests and synthetic dispute replay | Explicit supported numeric grammar; broad semantic contradictions not covered |
| Gemini durable receipts | Gemini/resume tests and recorded five-stage Phase 8 run | Historical models may be unavailable; unknown outcomes block repeats |
| Specialized public API | Phase 10 live acquisition and mixed-source graph tests | GB half-hour shares only; now explicitly selectable in full research |
| Docker/Render/CI | Private GitHub CI, image/nonroot/constrained research/reconnect/restore/health; official Render schema | Container execution verified; persistent hosted runtime remains open |
| Corrected benchmark and comparison runner | Frozen v2 dataset, 40 offline matched rows, durable 140-call Gemini cap and versioned rubric | Paid comparison was blocked before execution by the environment approval-credit limit; independent human review remains unclaimed |

## Submission readiness

- [x] Reproducible source installation and locked dependencies.
- [x] README, setup guide, final architecture diagrams, 3–5 minute demo script.
- [x] Executed synthetic coverage/dispute/repair/partial replays with inspectable support.
- [x] Measured evaluation table with N/A and failure qualifications.
- [x] Private data exclusions and local source/bundle verification workflow.
- [x] Delegated AI review of all 20 draft annotations and completed bounded Gemini execution; [5 October re-review](../evaluation/DELEGATED_REVIEW_2026-10-05.md) verifies all 40 saved fixture rows and proposes 16 narrower questions.
- [ ] Independent human validation and a defensible research-quality comparison (the approved paid run is blocked before execution by the environment approval-credit limit).
- [x] Private source repository and Docker runtime/remote CI verification.
- [ ] Persistent hosted storage/auth/access/capacity verification.
- [x] Read all 23 original-PDF pages and verify requirement/page mapping.
- [x] Implement original-PDF mixed-source/report/literal deduplication mechanics.
- [x] Verify actual live Tavily full pipeline with configured credential, one search, exact quotation checks and fresh-service recovery (deterministic reasoning).
- [x] Implement selected incremental production guidance; remote operation remains qualified.
- [ ] Any separate competition/instructor delivery rules, if applicable; none are stated in this PDF.

The final engineering check result is recorded in [Phase 11](../PHASE11.md).
Older audit counts are historical and overlap; they must not be added together.
