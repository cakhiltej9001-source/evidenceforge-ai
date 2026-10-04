# EvidenceForge AI progress



Updated: 4 October 2026, Asia/Calcutta.



## Current milestone



**Phase 9 evaluation implementation and initial experiments complete.** Human annotation
review and a successful matched Gemini full-agent comparison remain open, so Phase 9 is
not yet signed off as a validated research-quality benchmark. Phases 0–8 remain complete;
Phase 10 local source/runtime is verified and deployment configuration is prepared; Docker/host checks remain open. Phase 11 local submission materials and synthetic demonstration are prepared. See PHASE11.md and PHASE10.md. See `evaluation/PHASE9_REPORT.md` for measured results.

## Phase 0 history



Initial workspace contained only .git: master, no commits, application, tests or manifest.

No project/ancestor AGENTS.md was found; unrelated instructions were not adopted.

Planning created IMPLEMENTATION_PLAN.md and preserved CODEX_HANDOFF.md. All 19 requirement rows

(B01-B13/P01-P06) and the graph/routing/state/termination contracts were documented.

The handoff copy SHA-256 was verified against Downloads:

51EF84EE07AD0B8AA66D623511880FEA9B43E87625545093643E80CEC1764749.



Filename searches in workspace/Downloads/Documents/Desktop and likely archive-entry inspection

did not establish the original assignment PDF or companion instructions. All reported PDF pages

and the claimed 23-page count remain handoff-only, not independently verified.



## Phase 1 implemented



- Minimal src-layout package, pyproject.toml, uv.lock, .python-version, build backend and py.typed.

- .env.example and Git ignores for secrets, virtual environments, generated artifacts and local data.

- Explicit environment/dotenv configuration: fixture default, nested budgets, redacted errors/output.

- Validated request/question/context/query/source/acquisition/artifact/evidence/locator/rejection/gap/

  coverage/claim/link/report/critic/audit/error/budget/reservation/usage/call/event/message contracts.

- Stable content IDs versus fresh run/thread IDs; owner/content-version provenance.

- ResearchState channels, StateSnapshot validation, fresh initialization and pure partial updates.

- Immutable ID merges, provenance union, versioned call lifecycle, one-time reservation settlement,

  bounded diagnostic merges, deliberate overwrite/reset rules and terminal-data protection.

- Cross-reference, scope, content-version, UTF-8 evidence size, draft/audit and completion invariants.

- README setup/check instructions, SCHEMAS.md field explanations, DEVELOPMENT_CASES.md specifications,

  and DEPENDENCIES.md exact tested environment and gate results.



## Phase 1 verification history



| Check | Actual result |

|---|---|

| Locked setup | Python 3.12.13, uv 0.11.13; uv sync --locked passed |

| Offline contracts | 71 tests passed; network sockets blocked in tests |

| Lint and formatting | Ruff check and format check passed |

| Strict types | mypy passed for 7 source files |

| Config diagnostic | Fixture mode; credential fields excluded; unknown cost remains null |

| Packaging | uv build produced source distribution and wheel |

| Wheel installation | Actual wheel installed; isolated import from site-packages, config and state smoke passed |

| Environment restore | Locked editable package restored |

| Ignore/repository inspection | .env/data/.venv/dist ignored; project additions remain unstaged/uncommitted |



The tests include invalid data, preserved exact passage whitespace, duplicate provenance, replay,

unknown/dangling references, scope isolation, stale audits, terminal claims, fresh-state isolation,

actual LangGraph serialization and synthetic reducer wiring. These are contract tests, not measurements

of research accuracy, real budget enforcement or live provider quality.



## Phase 2 implemented



- Injected PlanningModel/ContextRepository protocols and deterministic/scripted offline fixtures.

- Manager validates fresh initialization and rejects stale counters/state.

- Planner validates focused questions/criteria and assigns scope-sensitive stable IDs.

- Context Manager selects bounded owner/request-scoped metadata; prior reports remain context only.

- Separate initialization result records; LangGraph fan-out and explicit all-predecessor join.

- Query Generator waits for both results, checks source availability, question links and allowances,

  merges normalized duplicates and skips attempted query keys without marking pending queries attempted.

- JSON/UTF-8 response caps, node timeouts, typed sanitized failures and explicit optional-context paths.

- PlanningService creates fresh runs and returns validated JSON state; no clients/keys enter state.

- Installed evidenceforge-plan command, labeled offline_fixture; live configuration rejected explicitly.

- PHASE2.md explains the graph, interfaces, scopes, status semantics and fixture limitations.



## Phase 2 verified results



| Check | Actual result |

|---|---|

| Offline locked setup | uv lock --offline and uv sync --locked --offline passed; no added dependencies |

| Offline tests | 131 passed in 4.46 seconds; 60 additional cases over the Phase 1 suite |

| Parallel join | Both branches wait for each other to start; query model called once after both finish |

| Structured failures | Invalid JSON/UTF-8, extra fields, duplicates, missing criteria and limits rejected |

| Scoped context | Other-owner/unrequested/disabled/duplicate/excess references discarded; query model not called |

| Optional context | Missing/unavailable/timed-out context disclosed; usable web planning continues |

| Query behavior | Stable IDs, association union, attempted-key filtering, source and search/pass limits verified |

| Offline guard | Ordinary loopback/external connects blocked; only stdlib socketpair setup permitted for Windows asyncio |

| Lint and formatting | Ruff check and format check passed |

| Strict types | mypy passed for 23 source files |

| Installed CLI smoke | 3 questions, 3 pending queries, offline_fixture/ready/running, 0 retrieval passes |

| Packaging | Offline wheel/sdist build passed; Phase 2 modules and planning entry point verified in wheel |

| Versions | Existing pinned LangGraph 1.2.12/Pydantic 2.13.5 and tool versions unchanged |



These tests check workflow mechanics and validated boundaries. Fixture templates do not demonstrate

live model reasoning, semantic atomicity, research accuracy, evidence quality or paid-call enforcement.

The successful planning snapshot remains run_status=running because research has not completed.

The CLI's default context repository contains no documents; a missing requested document is disclosed.



## Phase 3 implemented



- Provider-independent retrieval protocol and validated public-web result/batch/options contracts.

- Synthetic offline corpus/scripted adapter; Tavily REST adapter using HTTPX with explicit settings.

- Streamed response byte caps, bounded result/source sizes, timeout and no hidden retries/redirects.

- Source Processor with bounded parallel dispatch, durable pre-call reservations and stable identities.

- Standard-library SQLite search receipts; completed-response reuse and uncertain-call disclosure.

- Immutable owner/run-scoped UTF-8 artifacts with SHA-256/byte checks and atomic writes.

- Exact source snapshots, query/source/acquisition references and distinct content versions.

- Evidence Extractor with exact character offsets, lexical relevance, provenance union and rejection records.

- Evidence count/UTF-8 byte/per-source passage limits; excerpt-only acquisition labeling.

- Compiled retrieval subgraph, RetrievalService and installed evidenceforge-retrieve demo.

- Explicit one-search --live smoke; missing keys fail before search; no live search was run.

- PHASE3.md explains execution, operation receipts and limits; no report quality claims.



## Phase 3 verified results



| Check | Actual result |

|---|---|

| Locked setup | uv lock --offline and uv sync --locked --offline passed; 58 packages resolved |

| Offline tests | 183 passed in 56.50 seconds; 52 additional cases over Phase 2 |

| Strict types | mypy passed for 33 source files |

| Lint and formatting | Ruff check and format check passed |

| Source provenance | Exact snapshot slices, repeated acquisitions and duplicate association union verified |

| Empty/failed retrieval | No invented evidence; sanitized authentication/rate-limit/provider/schema/timeout errors |

| Bounds | Result/response/source/evidence/artifact caps, concurrency, search races and elapsed allowance verified |

| Durable receipts | Reservation-before-call, completed reuse, usage immutability and cancellation ambiguity verified |

| Storage isolation | Foreign scopes, corrupt snapshots and integrity mismatches rejected |

| Tavily contract | MockTransport verifies fixed endpoint/options, raw/excerpt handling, credits, streaming caps and no retry |

| Installed offline demo | One pass, one synthetic source, two admitted passages, zero errors; no report generated |

| Packaging | Offline wheel/sdist built; retrieval modules and CLI entry point verified in wheel |

| Live smoke | Not run; no real Tavily credential or external search was used |



A Windows path-length issue found by nested temporary-directory tests was corrected using shorter

physical hash names while retaining full record IDs/content hashes and integrity checks.

Lexical relevance is a heuristic, not semantic support or truth verification. The source is synthetic.

The SQLite ledger persists search operations; it is not a LangGraph workflow checkpointer.

One active retrieval invocation per run is supported, with concurrent searches inside its batch.

Unknown usage/cost stays null; a finite live dollar ceiling is refused without a pricing policy.



## Remaining scope and source gaps



No live model adapter, UI,

deployment or benchmark is implemented. A Tavily adapter exists but live behavior is untested. Typed support

verdicts do not establish factual truth. Producer sanitation and service/API authorization remain

requirements for later components.



Original PDF, companion AGENTS.md/setup, rubric/deadline, provider/model choice, paid-call budget,

live MCP obligation and private-data policies remain unresolved. They do not block further offline fixture work.



## Phase 4 implemented



- Full LangGraph routing with the existing parallel initialization join and bounded follow-up loops.

- Per-question criterion coverage, structured gaps, progress signature and no-progress stop.

- Validated draft claims/evidence references, versioned criticism and sanitized quality errors.

- Exact retained quote, locator/hash, question/citation and qualifier support checks for every claim kind.

- Shared critic/citation rewrite reservation; fresh audits and criticism after each rewrite.

- Supported-only final reports; historical blocking audits, explicit gaps/stop reasons and partial output.

- Markdown rendering, atomic report/state file writes and installed evidenceforge-research command.

- Immediate, genuine second-pass and no-evidence synthetic demos; PHASE4.md documents limits.



## Phase 4 verified results



| Check | Actual result |
|---|---|
| Final offline regression | 201 passed in 100.84 seconds; ordinary network connections blocked |
| New Phase 4 cases | 18 passing behavioral tests, including second-pass/repair/exhaustion/storage cases |
| Strict types | mypy passed for 41 source files |
| Lint and formatting | Ruff check and format check passed |
| Locked setup | uv lock --offline and uv sync --locked --offline passed; 58 packages, no added dependencies |
| Installed immediate demo | completed/sufficient; 1 retrieval pass; cited exact synthetic passages |
| Installed second-pass demo | completed/sufficient; 2 retrieval passes; separate retained solar and wind sources |
| Installed empty demo | insufficient_evidence/no_evidence; 3 bounded passes; unmet criteria disclosed |
| Revision safety | Unsupported claims repaired or omitted; critic/citation requests consume one shared rewrite limit |
| Failure paths | Unknown references, malformed drafts, corrupt snapshots, recursion and output-write failures checked |
| Packaging | Offline wheel/sdist built; Phase 4 modules and research entry point verified in wheel |
| Original handoff | SHA-256 unchanged: 51EF84EE07AD0B8AA66D623511880FEA9B43E87625545093643E80CEC1764749 |
| Live calls | None; end-to-end Phase 4 uses structured synthetic fixtures |

A UTF-8 encoding issue in the edited progress document was fixed; the subsequent repository format
check passed. Reports are saved for inspection, not resumable workflow checkpoints. Each output file
is atomic; the report/state pair is not transactional and an I/O failure prevents delivery confirmation.
Fixture lexical coverage and exact quotation support are not semantic verification or accuracy results.
Planning/query fixtures are separate from the quality_attempts counter; no paid usage is inferred.
Project additions remain uncommitted, as in earlier phases.



## Phase 5 implemented

- Bounded PDF/DOCX/TXT parsing, retained originals/hashes and canonical text with located chunks.
- Owner/request-filtered lexical lookup; source admission also checks cached result scope.
- PDF page, body paragraph and table-cell section citations with document hashes/retrieval dates.
- Textless/mixed PDF warnings and honest OCR limits; encrypted PDFs rejected.
- Chunk span/hash/location integrity, original-file replacement stability and storage size limits.
- Async SQLite LangGraph checkpoints, owner-scoped immutable registrations and pending-node resume.
- Process-released per-thread exclusive locks, configuration/identity checks and terminal redelivery.
- Separate prior-report summaries/navigation IDs, context selection and exclusion from evidence retrieval.
- Installed ingestion/document/pause/resume CLI commands and public synthetic energy TXT fixture.
- PHASE5.md documents commands, state/memory boundaries, parser and local security limits.

## Phase 5 verified results

| Check | Actual result |
|---|---|
| Locked setup | uv lock --offline and uv sync --locked --offline passed; 64 packages resolved |
| Full offline regression | 222 passed in 226.34 seconds, including actual two-process checkpoint resume |
| Strict types | mypy passed for 47 source files |
| Lint and formatting | Ruff check passed; format check passed for 70 files |
| Installed document demo | TXT ingested with 3 located chunks; report cited solar and wind paragraphs, original SHA-256 and retrieval dates |
| Installed pause/resume demo | Paused after source_processor; separate process resumed to completed/sufficient with 2 retrieval passes |
| Packaging | Offline wheel/sdist built; Phase 5 modules and ingest/research entry points verified in wheel |
| Live calls | None; demos used local document and synthetic fixture reasoning only |

These checks establish local workflow behavior and citation traceability, not factual accuracy or
OCR capability. The actual-process test uses a temporary file to capture Windows child output.

## Phase 6 implemented

- Validated ranking features, exact located numeric propositions, comparisons and graph records.
- Explicit general/current/historical weight profiles, unknown features and metadata rationale.
- Stable conservative copy-family grouping; duplicate quotations add no independent agreement.
- Decimal unit conversion with explicit entity/metric/timeframe/population/condition comparisons.
- Replacement analysis projections after each evidence batch, bounded counts and cap disclosure.
- Disputed coverage, primary-source/counter-evidence gaps and existing budgeted query routing.
- Evidence ordering by ranking, opposing claim links, partial output with both retained values.
- Graph/audit JSON, accessible tables and installed selected-claim inspection command.
- Exact quote/number/judgment validation, fresh initialization and graph-version 6 resume profile.
- Actual public synthetic demo exports in docs/examples/phase6; detailed steps and limits in PHASE6.md.

## Phase 6 verified results

| Check | Actual result |
|---|---|
| Full offline regression | 254 passed in 247.93 seconds; includes earlier separate-process restart/resume |
| New Phase 6 cases | 32 behavioral cases covering scope/unit/date/duplicates/ranking/tampering/graphs/caps/search limits/resume |
| Strict types | mypy passed for 54 source files |
| Lint and formatting | Ruff check and format check passed; 82 files already formatted |
| Locked setup | uv lock --offline and uv sync --locked --offline passed; 64 packages, no new dependencies |
| Installed dispute demo | partial/no_progress, 2 retrieval passes, 0 rewrites; both conflicting values retained |
| Actual comparison audit | 3 contradicts, 2 supports, 1 duplicate, 4 not_comparable records; synthetic only |
| Installed selected-claim inspection | JSON resolves 12 nodes and 24 edges from exported authoritative state |
| Packaging | Offline wheel/sdist rebuilt on 2 October 2026; packaged Phase 6 modules match current source and inspect entry point is verified |
| Handoff integrity | Original SHA-256 unchanged: 51EF84EE07AD0B8AA66D623511880FEA9B43E87625545093643E80CEC1764749 |
| Local-data isolation | Runtime reports/checkpoints remain Git ignored; only public synthetic example artifacts copied into docs |
| Live research / accuracy benchmark | None; no research-quality or cost improvement claimed |

Numeric comparison supports only documented explicit scoped sentences. Other prose remains
unclassified; unknown metadata stays unknown. Rankings are heuristics. The graph-version change
refuses Phase 5 workflow registrations rather than silently changing their pending routing.
Project additions remain uncommitted, consistent with earlier milestones.

## Phase 7 implemented

- Durable owner-scoped cancellation requests; paused runs finalize on resume, while active adapter
  waits stop cooperatively. Cancelled in-flight receipts remain ambiguous and consume reservations.
- Planning/query model attempts share the model-call ceiling with quality attempts; exploratory
  calls preserve the configured quality allowance. Search retries reserve separate SQLite receipts.
- Retry policy permits only adapter-declared safe transient categories. Tavily opts into 429 only,
  with bounded Retry-After guidance; no implicit provider/scope fallback is configured.
- HTTP(S) source URL admission rejects embedded credentials, loopback/non-global IPs and local or
  internal hostnames. Retrieval content stays data under fixed graph nodes and source-tool scopes.
- Dated configurable price table and usage summaries report unknown tokens/costs as unknown.
- Opt-in LangSmith custom sink receives allowlisted counters only; ambient raw graph tracing is
  disabled. Saved progress and local trace coverage report actual emissions, failures and unverified
  remote delivery.
- Installed research CLI exposes --cancel and prints usage/progress/trace-coverage paths.
- The graph resume profile is version 7; Phase 6 pending registrations are rejected rather than
  resumed under changed budget and cancellation rules. Their report exports remain readable.
- Detailed steps, commands, security boundary and limits are in PHASE7.md.

## Phase 7 verified results

| Check | Actual result |
|---|---|
| Full offline regression | 261 passed in 478.01 seconds after consolidated accounting and cancellation changes |
| Later focused tests | 4 passed for LangSmith payload allowlist, nonfatal sink failure, HTTP 429 Retry-After and adversarial retrieved content; these were added after the full run started |
| Strict types | mypy passed for 58 source files |
| Lint and formatting | Ruff check passed; format check passed for 88 files |
| Locked setup | uv lock --offline resolved 64 packages; installed CLI used uv run --locked --offline |
| Packaging | Offline source distribution and wheel rebuilt after final code edits |
| Installed two-pass demo | completed/sufficient, 2 passes; usage recorded 3 search reservations, 7 model attempts and unknown cost as null |
| Installed cancellation demo | paused at query generation, --cancel accepted owner-scoped thread, --resume delivered cancelled/cancelled with 0 passes |
| LangSmith remote | Not invoked; local trace hook payloads tested with a fake client, remote delivery explicitly unverified |
| Live research / accuracy | None; end-to-end run remains offline synthetic fixture reasoning |

The old low model-call test now stops before query generation because a 3-call ceiling with 2 quality
calls reserved leaves no query-generation slot after planning. The tests assert this conservative
behavior. Search limit races, no-progress stops and actual-process restart/resume remain in the full
regression. Actual model token usage and provider prices are unavailable in fixture runs; no dollar
cost or live trace coverage is inferred. Project additions remain uncommitted.

## Next action: Phase 8 only

Build the interaction/export layer only when authorized. Original assignment reconciliation remains
required before final project sign-off.


## Gemini setup and integration — 2 October 2026

User selected Gemini and the latest model. The local, Git-ignored .env now selects
gemini / gemini-3.8-flash and contains the supplied private key; no secret value is recorded here.

- Google's current model catalogue identifies Gemini 3.8 Flash as its latest stable text model.
- Authenticated model lookup returned HTTP 200 for models/gemini-3.8-flash.
- A bounded structured-planning generation smoke returned HTTP 400. Google's sanitized message
  reported high demand; successful live generation remains unverified. No provider fallback enabled.
- Added a stateless httpx Gemini adapter for planning, queries, coverage, synthesis and critique.
  JSON schemas and application validators bound outputs; final text remains exact retained quotations.
- The research CLI requires explicit document IDs or a labeled synthetic demo for Gemini.
  No live web research was enabled. Standalone planning/retrieval CLI demos remain fixture-only.
- Conservatively reserved input/output token allowances, per-run call limits, no automatic retries,
  response size limits, timeouts, fixed provider host, header authentication and disabled redirects.
- Provider usage observations are exported separately as model_usage.json when available; missing
  usage and estimated dollar cost remain unknown. Dollar caps require a verified price policy.
- Paid pause/resume is refused until durable model-call reconciliation exists. Fixture checkpoint
  resume remains available with --offline. A fresh adapter/service is required for each paid run.
- Gemini transport/integration tests: 19 passed, including a complete simulated graph, credential
  redaction, HTTP failures, response-size limits, token/call caps, and CLI evidence requirements.
- Existing configuration/research tests: 27 passed during this change.
- Ruff check passed; strict mypy passed for 59 source files before the final docstring edits.
- Installed settings checker reported gemini / gemini-3.8-flash without exposing credentials.

This is a provider setup addition; it does not mark Phase 8 or later phases complete.
- Final installed offline smoke: completed/sufficient, two retrieval passes, zero rewrites.
  Saved under .evidenceforge/gemini-setup-offline-smoke/reports/run_b40938a32cce43b08d5ba4e513952e61/.
- Final format check: 74 files already formatted. Final strict mypy: 59 source files passed.


## Phase 0–7 verification before Phase 8 — 2 October 2026

Fresh final regression: **302 passed in 389.78 seconds**, no failures or skips.
The initial audit exposed 3 private-dotenv-dependent CLI failures (281 passed); those are fixed.
A focused 96-test repair run also passed and overlaps the final full suite.

- Added basic accepted/rejected/needs_clarification input review before new service work.
- Test defaults shadow private dotenv provider/model/key values with fixture/blank settings.
- Corrected structured coverage labels and stale planning/Phase 7 setup documentation.
- Ruff check passed; 76 files formatted; strict mypy passed for 60 source files.
- uv lock --check --offline passed (64 packages). Current wheel/sdist built offline.
- All 60 Python sources match the wheel; isolated wheel planning/import smoke passed.
- No private config/data or supplied key found in either distribution.
- Eight installed CLI scenarios passed: planning, retrieval, two-pass, empty, dispute,
  selected-claim inspection, document ingestion/research, and cancellation/resume.
- Fresh Gemini model lookup passed HTTP 200; one bounded generation attempt returned HTTP 503.
  Successful live generation remains unverified. Paid Gemini resume remains disabled.

**Ready to begin Phase 8 for the verified local/offline foundation. Phase 8 has not started.**
Original PDF/rubric reconciliation, live web/external-source verification, paid model recovery,
remote trace delivery and research-quality evaluation remain separate open gates.
Full audit and requirement mapping: PHASE0_7_VERIFICATION.md.
Machine results: .evidenceforge/verification/phase0-7/ (Git ignored).


## Gemini retry and lighter-model checks — 2 October 2026

- Retried configured gemini-3.8-flash: HTTP 503, provider reported temporary high demand.
- gemini-3.5-flash-lite model lookup: HTTP 200. Structured generation: HTTP 400 INVALID_ARGUMENT, without a specific argument diagnostic.
- Flash-Lite compatibility probes with responseFormat, default thinking and stateless Interactions API also returned HTTP 400. No request-format cause established.
- gemini-3.6-flash structured generation: HTTP 400 INVALID_ARGUMENT.
- gemini-2.5-flash-lite: HTTP 404, provider says this legacy model is unavailable to new users.
- No model produced a validated live plan; saved model remains gemini-3.8-flash. No source code or credential changes.
- Sanitized attempt artifacts: .evidenceforge/verification/gemini-retries/ (Git ignored). Phase 8 remains unstarted.

## Phase 8 implementation — 2 October 2026

- Dedicated plan interrupt before query generation/retrieval; strict boolean and current-plan decision.
- CLI --require-approval, --approve-plan VERSION and --reject-plan VERSION.
- Owner-scoped checkpoint snapshot/reconnect inventory; graph version 8 (no silent Phase 7 migration).
- Streamlit 1.64.0 optional extra, localhost launcher, bounded background UI service operations.
- Local document upload, plan review, allowlisted progress, cancel, resume/reconnect, claim inspection.
- Markdown and allowlisted report JSON downloads; finalized service delivery saves report.json.
- Six backend integration tests passed (115.24 s); two Streamlit AppTest/upload tests passed (141.39 s).
- Separate-process CLI plan approval/resume passed with two retrieval passes and JSON export.
- Ruff passed; strict mypy passed for 65 source files; lock check passed (91 packages).
  Streamlit third-party internals are excluded from type traversal; our UI/service code remains checked.
- Local server health returned HTTP 200 at 127.0.0.1:8501. Codex preview requested.
- Full regression suite and distribution verification are still in progress.
- Main Gemini and fallback generation failures remain unresolved; UI uses offline reasoning.

## Phase 8 final verification — 2 October 2026

**Phase 8 complete for the local/offline foundation. Phase 9 has not started.**

- Final full suite: **314 passed in 549.94 s**, no failures/skips.
- Includes versioned plan editing and renewed approval, scoped event/export reads,
  live sanitized timeline/coverage/usage/audit views and pre-provider paid-control rejection.
- Initial failures fixed: checkpoint internal channels rejected by strict state validation;
  early planner failures incorrectly finalized as insufficient_evidence instead of failed.
- Targeted repair: 26 passed (306.23 s); edited-plan/UI checks: 4 passed (46.54 s).
  These overlap the final suite and are not additional unique tests.
- Separate-process edited-plan CLI smoke passed: plan version 1 -> edit version 2 -> approve/resume.
- Per-step progress-file writes removed: UI reads validated checkpoints, and finalized
  progress.json remains available. The workbench reuses its read service.
- Final Ruff check/format passed; strict mypy passed for 65 source files; lock check passed.
- Final wheel/sdist rebuilt; current source and optional UI/entry-point checks verified.
- App runs on localhost at http://127.0.0.1:8501; setup/control details: PHASE8.md.
- Gemini generation and durable paid resume, original PDF/rubric reconciliation, live web/
  external sources, deployed authentication and research-quality evaluation remain open.

## Gemini generation and paid resume repair — 2 October 2026

- Gemini 3.8 again returned HTTP 503. The authorized 3.5 Flash Lite fallback generated successfully.
- Fixed rejected provider schemas by normalizing unsupported metadata and preserving finite purpose
  constraints as enums. Full Pydantic response validation remains enforced.
- Configured the private `.env` to use `gemini-3.5-flash-lite`; no credentials were printed or exported.
- Added scoped durable SQLite model-call reservations/results, immutable model/budget registration,
  completed-response replay and automatic retry blocking for failed/unconfirmed calls.
- Enabled paid plan approval/edit/resume in ResearchService, CLI and Streamlit. Reconnect restores
  the registered model and original budget. Historical paid runs without receipts cannot migrate.
- Live five-stage workflow completed after an edit to version 2 and cross-service approval/resume:
  `run_18f6eee6b2044a999097c6901eec2919`, two quoted claims, five successful calls, 5,692 tokens.
  Terminal reconnect and a separate CLI process made no additional model calls.
- 35 affected adapter/approval/UI tests passed (129.70 s); final five receipt/schema tests passed
  (36.87 s), overlapping coverage. The prior 314-test baseline was not rerun for this repair.
- UI facade reconstructs the saved model and reads durable known-token counters without paid calls.
- Synthetic evidence does not establish source truth. Live web retrieval, original assignment
  reconciliation, deployed authentication and research-quality evaluation remain open.

Artifacts: `.evidenceforge/verification/gemini-resume/` (ignored local data).

## Phase 9 evaluation — 3 October 2026

- Frozen 20-case synthetic draft dataset: 12 development, 8 held out.
- Local one-pass and full-agent comparison: all 40 variants executed; 0 missing.
  Full-agent required-aspect coverage was 1.0 on both partitions. One-pass coverage
  was 0.5 development and 0.6667 held out; noncompleted statuses are reported.
- Gemini one-shot baseline: 12 usable of 20 cases. Eight earlier calls failed or
  remained unconfirmed; no unverified score was filled in.
- Durable paid ledger reserved 26 of the authorized 30 Gemini calls: 23 HTTP 200,
  two HTTP 429, one unconfirmed. Two matched full-agent probes ended partial/failed.
- Repaired compressed HTTP response handling and added a regression test. Separated
  noncompleted workflow outcomes from truly missing runs.
- Five focused evaluation tests and 23 Gemini/resume regression tests passed;
  Ruff and mypy checks passed for edited evaluation modules.
- Original freeze and post-freeze amendment hashes, review checklist, and full
  limitations are in `evaluation/PHASE9_REPORT.md` and `evaluation/REVIEW.md`.
- Independent human review of 20 draft annotations and a successful matched
  provider comparison remain pending before Phase 9 validation sign-off.


## Phase 9 pending-item audit — 3 October 2026

- Prepared `evaluation/ANNOTATION_PACKET.md` with all 20 cases and complete
  synthetic dispute context; `ANNOTATION_AUDIT.json` reports 20 passing
  structural checks. Independent semantic review remains pending.
- Exact request-body hashes linked all 20 one-shot cases to durable model receipts.
  Twelve successful calls had 1,780 verified tokens; eight call usages are unknown.
  Historical per-case latency remains N/A; future runs now record it.
- Recovered known Gemini model usage for both bounded workflow probes.
- Corrected citation scoring so an uncited audited claim cannot inflate
  precision. All 40 saved fixture scores were recomputed unchanged.
- Clarified that the two Gemini probes had smaller budgets than the fixture full
  variant, so they are diagnostic and not matched quality comparisons.
- The 30-call paid cap remains intact: 26 reserved, four unused. A complete live
  comparison needs a new authorized budget and provider availability.


## Phase 9 extension readiness — 4 October 2026

- Fixed missing-ledger dry-run mutation, protected original output, checked
  sufficient execution allowance, and froze source/base-result hashes.
- Extension dry run: eight missing one-shot cases, two full-agent cases, at most
  32 attempts under the proposed separately authorized 40-call allowance.
- Final relevant checks: 33 tests passed (77.19 s); Ruff and mypy passed.
- No new Gemini calls: original ledger remains 26/30. Additional budget approval
  and completed independent annotation review are still required for sign-off.
- Read `evaluation/EXTENSION_PLAN.md` and `evaluation/ANNOTATION_PACKET.md`.

## Phase 10 source and deployment preparation — 4 October 2026

- User explicitly authorized moving to the next phase while Phase 9's independent
  review and successful matched provider comparison remain open.
- Added a read-only NESO GB half-hour generation mix adapter with one fixed GET
  endpoint, no credentials, no redirects/retries, bounded response/source sizes,
  typed errors and strict fuel/percentage/period schema checks.
- Added `evidenceforge-energy`: synthetic default; explicit `--live` acquisition
  through existing receipt/snapshot/evidence machinery with no model API calls.
- Live acquisition succeeded: `run_2b485ed0acce41fcbed9ea005c604c3f`, one source,
  eight located passages including solar/wind, no errors. Returned interval was
  3 October 2026 18:30–19:00 UTC. Values are projected percentage records, not
  provider-authored prose or absolute MWh. Interval is not treated as publication time.
- Prepared nonroot Docker image, build-context allowlist, localhost Compose and
  persistent volume, private Render single-instance/disk template and CI checks.
- Hosting checks use current official Render documentation; free/ephemeral storage,
  process interruption, private access and in-process job limits are documented.
- Local offline smoke passed acquisition, approval, fresh-service resume, terminal
  checkpoint reconnect and report JSON/Markdown export; no provider calls.
- Final 44 focused source/regression tests passed (11.39 s); repository Ruff/format
  checks and strict mypy (71 source files) passed. Earlier runs overlap.
- Locked offline UI installation passed (91 resolved packages); YAML syntax passed.
- Wheel/sdist build, wheel entry-point/module checks and installed offline energy
  command passed. Temporary UI health on 127.0.0.1:8502 returned HTTP 200.
- Docker is not installed: image/runtime checks and remote CI/platform verification
  remain open. No paid resources or public deployment were created. Gemini stays
  at the original 26/30 evaluation allowance. See `PHASE10.md`.


## Phase 10 pending-item repair — 4 October 2026

- Official Render JSON schema validation passed, zero errors; added reusable
  validator and matching CI check. This does not create or verify a hosted instance.
- Separate-process checkpoint/report reconnect passed. Synthetic data archive,
  restore to a separate directory and restored-process reconnect also passed.
- Container CI now tests full offline research/checkpoint persistence across fresh
  containers rather than only retained energy JSON; script lint/format/YAML passed.
- Docker local prerequisites are unmet: about 4 GB RAM, firmware virtualization
  reported disabled, unusable WSL status and no Docker installation. Feature
  queries require administrator elevation. Hosted CI is the proposed execution route.
- GitHub authentication succeeded outside the sandbox. There is no Git remote,
  matching research repository or configured Render access. A private repository
  creation/upload/CI run and hosting target have been requested from the user.
- Additional Gemini cap and independent 20-case review are also awaiting replies.
  No paid calls, OS changes, repository publication or hosting resources were made.
- Evidence/steps and exact remaining dependencies are in PHASE10.md.

## Phase 11 submission and demonstration — 4 October 2026

- User authorized continuing to the next phase with prior external gates open.
- Reworked README; prepared setup guide, implemented architecture diagrams,
  B01–B13/P01–P06 checklist, measured evaluation table and honest limitations.
- Added a 4 minute 30 second demo script and local clickable replay generator.
- Fresh actual offline service runs demonstrated two-pass coverage, a dispute,
  one deliberate unsupported-draft repair, and a pass-limited partial result.
- Replay retains reports, audits, state and per-claim support graphs; fixture
  content and deliberate fault injection are explicitly labeled synthetic.
- Full final regression: 349 passed in 694.19 seconds. Ruff lint and format passed.
- No new Gemini calls, repository upload, Docker installation or hosting resources.
- Local Phase 11 deliverables are prepared; assignment PDF/rubric reconciliation,
  Phase 9 review/provider comparison and Docker/host verification remain open.
- See PHASE11.md and submission/DEMO.md for reproduction and qualification.
- Final static typing passed (71 source files); wheel/sdist build passed; 53 documentation/replay links and four saved states verified.

## Pending-gate audit — 4 October 2026

- Fresh public NESO acquisition passed (run_f469bad1cb474e7398def41ad32a77da); Phase 9 extension dry run planned 32 maximum new attempts, with no paid calls.
- Docker executable and Git remote remain absent; Tavily and Render credentials absent. Human review, original assignment PDF/rubric, extra Gemini allowance and private hosted CI decisions remain open.
- See PENDING_AUDIT_2026-10-04.md for exact evidence and next inputs.


## Pending work repair — 4 October 2026

- Prepared Docker CI resource bounds, nonroot assertion and fresh-volume backup/restore reconnect; YAML parsed. Container runtime remains unverified.
- Added an offline human annotation form and instructions; all 20 cases require decisions, none preselected. HTTP and JavaScript syntax checks passed.
- Ruff lint and format passed (127 files). Known credential/private-path source preflight passed; pinned setup-uv action commit exists.
- Automatic approval review rejected the new 40-call Gemini execution before it ran because only the original 30-call cap is explicit. Separate Gemini and private GitHub/CI approval requests remain pending.
- Original PDF/rubric, hosting target, independent reviewer and Tavily credential remain missing. See PENDING_FIX_2026-10-04.md.

## Delegated pending execution — 4 October 2026

- The user instructed Codex to perform the pending work on their behalf after the explicit 40-additional-call and private GitHub CI request.
- The separately capped Gemini extension is now authorized and running. The original 30-call ledger remains separate and unchanged.
- Private `cakhiltej9001-source/evidenceforge-ai` repository creation, source upload and prepared CI execution are authorized; the repository did not already exist.
- Codex will record its 20-case review as AI review, preserving the distinction from independent human annotation sign-off.
