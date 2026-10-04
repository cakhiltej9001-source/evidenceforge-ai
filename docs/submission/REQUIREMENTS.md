# Requirements and submission checklist

Status is against the preserved handoff and implemented repository. The original
assignment PDF, judging rubric and deadline have not been supplied. Page mappings
in the historical plan remain unverified; this checklist cannot establish rubric
compliance. Paths below are relative to `src/evidenceforge/` unless marked otherwise.

## Baseline traceability

| ID | Requirement | Implementation/evidence | Status and qualification |
|---|---|---|---|
| B01 | Focused subquestions and criteria | `nodes/planner.py`, `schemas.py`; `tests/test_planning.py` | Implemented and locally tested |
| B02 | Web/document/external source paths | `retrieval/tavily.py`, `retrieval/documents.py`, `retrieval/carbon_intensity.py`; retrieval/document/Phase 10 tests | Document and fixture paths verified; NESO live acquisition verified. Tavily live access and any specifically required MCP obligation remain unverified |
| B03 | Manager coordinates planning/context | `graph/research.py`, `nodes/manager.py`, `nodes/context.py`; planning tests | Implemented all-predecessor join; one downstream initialization |
| B04 | Source-specific bounded queries | `nodes/queries.py`; `tests/test_planning_queries.py` | Implemented, including follow-up queries |
| B05 | Exact evidence, duplicates and provenance | `nodes/sources.py`, `nodes/extraction.py`, `storage/artifacts.py`; retrieval tests | Implemented; lexical relevance is not truth verification |
| B06 | Shared state and replay-safe reducers | `graph/state.py`, `graph/reducers.py`; `tests/test_state.py` | Implemented contracts, cross-references and bounded records |
| B07 | Coverage gaps trigger another pass | `nodes/quality.py`, `graph/research.py`; `test_second_pass_adds_new_evidence` | Verified synthetic two-pass demo |
| B08 | Bounded stop with disclosed gaps | `nodes/quality.py`, `reporting.py`; `test_pass_limit_returns_partial_with_gaps` | Verified partial/pass-limit path and other stop conditions |
| B09 | Required report sections and sources | `reporting.py`, `exports.py`; research/Phase 8 tests | Markdown/JSON delivery implemented |
| B10 | Critic and shared revision budget | `nodes/quality.py`; critic/citation allowance tests | Implemented; exhausted repairs cannot manufacture completion |
| B11 | Trace claims to evidence | `nodes/quality.py`, `evidence/projection.py`; audit/support tests | Exact quotations and snapshot integrity verified; independent source truth/semantic accuracy not established |
| B12 | Registered compiled LangGraph | `graph/research.py`, `graph/builder.py`; planning/research tests | Implemented and executed |
| B13 | SQLite thread checkpoints and restart | `storage/checkpoints.py`, `services/research.py`; persistence/Phase 8 tests | Local process restart and scoped reconnect verified; hosted durability unverified |
| P01 | Secrets/environment configuration | `config.py`; config tests and Git/Docker excludes | Keys private/redacted; optional provider requests require explicit configuration |
| P02 | Input validation/clarification | `guardrails.py`; `tests/test_guardrails.py` | Deterministic schema/topic policy; not a semantic answerability classifier |
| P03 | Progress, usage and traces | `services/observability.py`, `services/usage.py`; Phase 7/8 tests | Sanitized local observability; unknown tokens/cost disclosed; remote tracing not verified |
| P04 | Typed errors and bounded fallback/retry | Retrieval/model adapters, `services/retry.py`; provider/guardrail tests | Permitted retrieval retries bounded; Gemini fallback manually configured; failed/uncertain paid calls cannot auto-retry |
| P05 | Bounded evidence and prior context | `nodes/extraction.py`, `storage/local_context.py`; persistence/guardrail tests | Implemented byte/count bounds; prior reports remain context |
| P06 | Phase-specific read-only tools | Model/retrieval contracts and service dependency injection | No arbitrary write/code-execution tool offered to research models |

## Additional implemented features

| Feature | Evidence | Limit |
|---|---|---|
| Plan approval/editing | Phase 8 tests, local deployment smoke | Owner IDs are not authentication |
| Claim graph and selected support | `evidence/projection.py`, UI, Phase 11 replay | Projection of retained records; no independent truth score |
| Dispute/unit/date/source-family handling | Evidence intelligence tests and synthetic dispute replay | Explicit supported numeric grammar; broad semantic contradictions not covered |
| Gemini durable receipts | Gemini/resume tests and recorded five-stage Phase 8 run | Historical models may be unavailable; unknown outcomes block repeats |
| Specialized public API | Phase 10 live acquisition and schema/receipt tests | GB half-hour shares only; separate from full research graph |
| Docker/Render/CI | Private GitHub CI, image/nonroot/constrained research/reconnect/restore/health; official Render schema | Container execution verified; persistent hosted runtime remains open |
| Draft benchmark and comparison runner | 40 fixture variants, 20 usable Gemini one-shots, preserved extension failures and AI review | Broader research-quality validation and independent human review remain unclaimed |

## Submission readiness

- [x] Reproducible source installation and locked dependencies.
- [x] README, setup guide, final architecture diagrams, 3–5 minute demo script.
- [x] Executed synthetic coverage/dispute/repair/partial replays with inspectable support.
- [x] Measured evaluation table with N/A and failure qualifications.
- [x] Private data exclusions and local source/bundle verification workflow.
- [x] Delegated AI review of all 20 draft annotations and completed bounded Gemini execution.
- [ ] Independent human validation and a defensible research-quality comparison.
- [x] Private source repository and Docker runtime/remote CI verification.
- [ ] Persistent hosted storage/auth/access/capacity verification.
- [ ] Original assignment PDF and rubric reconciliation, including any mandatory MCP requirement.
- [ ] Competition deadline, required submission format and final approval to publish/upload.

The final engineering check result is recorded in [Phase 11](../PHASE11.md).
Older audit counts are historical and overlap; they must not be added together.
