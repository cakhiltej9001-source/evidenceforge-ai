# Foundation, planning and retrieval contracts

The schema module validates data shapes and references. It does not establish source truth,
extract passages, call providers, reserve money, or execute research. Those services arrive later.

## Identities and records

stable_id(namespace, *parts) hashes canonical JSON; field ordering does not change the hash.
Include owner scope and content version when identifying private content. new_id creates a fresh
run/thread identity. Stable IDs enable replay/deduplication; they do not authenticate an owner.

Record models forbid extra fields, validate defaults and use immutable fields/tuple collections.
They revalidate model instances at boundaries, including instances created with model_copy.
Numeric counts reject booleans/strings; scores/costs reject booleans, NaN, infinity and invalid ranges.
Aware timestamps include a timezone. JSON serialization uses model_dump(mode="json").
Exact passage whitespace is preserved; offsets count Unicode characters, not UTF-8 bytes.

| Record | Important fields and purpose |
|---|---|
| ResearchRequest | Original question, owner_scope, requested document IDs, preferences and mode |
| InitializationResult (Phase 2) | Unique planner/context_manager role and ready/unavailable/failed status |
| ResearchQuestion | Stable ID, atomic question, answer criteria and importance |
| ContextReference | Owner-scoped document/prior-report ID; the repository must still authorize access |
| SearchQuery | Question IDs, source type, pass number, purpose and query text |
| SourceRecord | Location, content hash/version, provider, publisher/date/source family; private documents require ownership |
| SourceAcquisition | Query/source/snapshot association and retrieval time; preserves repeated acquisitions |
| ArtifactReference | Relative storage key, content hash, parser version and byte count; contains no raw page/client |
| EvidenceItem/Locator | Exact passage, snapshot/offset/page location, owner, question/acquisition links and relevance |
| RejectedEvidence | Candidate/source and reason; rejection is inspectable rather than discarded |
| ResearchGap/QuestionCoverage | Missing aspects/follow-up and per-question evidence/status; sufficiency needs evidence |
| Claim/ClaimEvidenceLink | Statement kind/qualifiers and evidence relationships; drafts can contain uncited claims for later audit |
| Report/ReportSection | Versioned placement of claim IDs and source IDs; no free-form unaudited prose/URLs |
| CriticVerdict | Versioned approval or actionable revision brief |
| CitationAuditItem | Versioned claim audit, structural validity, support judgment, evidence and repair action |
| BudgetLimits/Reservation | Immutable configured limits and a recorded call allowance; no spending service yet |
| CallRecord | Request hash, provider, timestamps, response reference and versioned lifecycle |
| UsageRecord | Call identity, measured/unknown usage, latency and dated cost estimate |
| ToolError/RunEvent/ResearchMessage | Bounded diagnostic records; producers must sanitize messages before admission |

Unknown tokens and cost remain null. A zero cost estimate requires a price-table version;
missing metadata never silently becomes a free call. Source URL validation accepts HTTP(S)
and forbids embedded credentials; URL-fetch security belongs to the later retrieval boundary.

## Shared state

ResearchState is a TypedDict declaring graph channels/reducers. StateSnapshot validates a complete
snapshot, references and structural invariants. validate_state returns a fresh JSON-only dictionary.
apply_update validates a pure partial update. Future graph nodes must use these boundaries;
a raw TypedDict and LangGraph compilation alone do not perform runtime semantic validation.

- run_id/thread_id/owner_scope/schema_version/request/budget are immutable within apply_update.
- research_questions/plan_version and context_refs are separate initialization branch writes.
- planning_status tracks not_started/initializing/ready/failed independently of research completion.
  initialization_results merges one stable record per branch; ready requires both branch outcomes
  and versioned planner questions. Planner is required; optional context may be unavailable.
- search_queries is the current batch; query_records preserves query history for provenance.
- Immutable source/artifact/query/usage registries merge by ID; conflicting payloads fail.
- Evidence merges union question/acquisition associations while preserving passage/locator identity.
- Coverage, gaps, current report/claims, critic verdict and audit overwrite their prior version.
  Reset stale verdict/audit together with a rewritten draft; report section IDs must cover all claims.
- Pass/rewrite/plan counters have one writer, cannot move backwards through apply_update, and
  cannot exceed configured limits. A research pass counts completed retrieval batches.
- Events/messages/errors merge by ID with a 200-record checkpoint cap. Empty updates do not clear
  merged channels. After archiving diagnostics, Overwrite({}) explicitly resets these logs.
  apply_update rejects Overwrite for evidence, usage and other authoritative registries.
- initial_state creates a fresh run/thread, empty registries and zero counters; pass the previous
  saved state through validate_state to resume instead of calling initial_state.
- Source acquisitions must match source/snapshot content versions. Evidence and context owners
  must match the run. A thread ID is not authorization; repository/API checks remain necessary.
- Completed runs require a current nonempty final/draft report, full coverage, critic approval and
  supported audits for every factual claim. This checks recorded verdicts, not their factual truth.

Calls and reservations are mutable lifecycle records with specialized reducers. A pending call can
advance to completed/failed/ambiguous/cancelled with a higher revision; ambiguity may later be resolved.
Stale call versions cannot roll back a recorded response; same-version conflicts and changed request
identity fail. Reserved capacity settles or releases once; replay cannot restore it. Usage is unique
by call ID even if two distinct usage record IDs are supplied.

No ledger persistence, budget transaction, restart service or real SQLite checkpointer is implemented
in Phase 1. The checkpoint serialization test exercises LangGraph's actual serializer, and a tiny
synthetic graph checks reducer wiring; neither test implements the research nodes.

## Configuration

Settings loads EVIDENCEFORGE_ variables; load_settings accepts a dotenv path (default .env).
Environment values override dotenv, then defaults. Nested budget settings use BUDGET__FIELD.
Empty model/key entries mean unconfigured. Fixture mode needs no credentials and tracing defaults off.
Live settings require an explicit provider, model ID and nonblank model key; adapters arrive later.

Keys use SecretStr and are excluded from repr/dict/JSON output. Public loader errors report field names
rather than raw values. Settings never creates directories or places clients/credentials into state.
Do not pass raw exception inputs or untrusted source text to diagnostics; message sanitation is a
producer responsibility and is not proven by string types.

Official references checked 30 September 2026:
[Pydantic models](https://docs.pydantic.dev/latest/concepts/models/),
[Pydantic settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/),
[LangGraph graph/state/reducers](https://docs.langchain.com/oss/python/langgraph/graph-api),
[uv locking](https://docs.astral.sh/uv/concepts/projects/sync/).


Completed or otherwise terminal research data cannot be changed through apply_update; start a fresh run. Diagnostic log updates remain allowed. Report source IDs must exactly match the evidence cited by current claims, and structurally valid audit items must cover those same citation IDs.

## Phase 2 output boundaries

planning.py defines PlanDraft/QuestionDraft, QueryBatchDraft/QueryDraft, ContextBatch and
QueryGenerationRequest. These carry validated data across injected interfaces; nodes assign IDs.
PlanningOptions bounds context references, response bytes and node timeout. See PHASE2.md for
normalization, limits, scoped-context selection and fixture-only status semantics.

The offline planning graph is executable; retrieval, reports, persistent checkpoints and real
provider/usage integrations remain later milestones. Structural validation is not a factual audit.

## Phase 3 retrieval boundaries

RetrievedSource/RetrievalBatch validate public web text, content scope and optional measured credits.
RetrievalOptions caps result/response/source/artifact/passage sizes and timeout.
CallReceipt wraps owner/run identity, call/reservation, retained response, usage and typed failure.
CallLedger atomically reserves search capacity and persists operation receipts; it is separate from
future workflow checkpoints. ArtifactStore verifies exact UTF-8 bytes and full content hashes.

RejectedEvidence now includes evidence_limit/content_limit/snapshot_limit/unavailable_content in
addition to existing reasons. Source Processor/Evidence Extractor use the existing state channels.
An acquisition exposes full_text versus search_excerpt; exact offsets refer to the retained snapshot,
not an independently verified original web page. See PHASE3.md for limits and recovery semantics.

## Phase 4 quality boundaries

research.py defines CoverageInput/CoverageAssessment with indexed criterion support, ReportDraft with
claim references, SynthesisInput, CriticInput/CriticAssessment and bounded ResearchOptions.
State adds quality_attempts, revision_brief, stage_error, coverage_signature, last_coverage_pass,
no_progress_count and historical unresolved_audits. Current draft audits remain version-checked;
removed unsupported claims keep historical audits separately. quality_attempts is a fixture counter,
not a paid-call usage measurement. See PHASE4.md for routing and conservative support semantics.

## Phase 5 document and persistence boundaries

DocumentOptions bounds input, extraction, chunks, archive expansion and stored original bytes.
DocumentRecord records owned binary/text/chunk-metadata hashes, status, warnings and ingestion time.
DocumentChunk records exact canonical spans and page/paragraph/table locations. RetrievedDocument
adds scoped document/chunk IDs and binary hash; RetrievalBatch now accepts public web or located
private-document results. SourceAcquisition and EvidenceLocator retain document offsets separately
from retained snapshot offsets; SourceRecord carries optional document hash/chunk identity.

RunRegistration stores immutable initial identity/request/budgets plus a graph/client/options profile.
Actual pending graph steps live in the separate async SQLite checkpointer. PriorReport stores bounded
generated summaries, original source/evidence navigation IDs and context-only classification. These
records are not retrieved as independent evidence. See PHASE5.md for exact scoping and resume limits.

## Phase 6 analysis and inspection boundaries

SourceRecord/RetrievedSource accept supplied publisher/date/family and optional primary/methodology
hints with a required rationale. AnalysisOptions bounds propositions/comparisons and chooses an
explicit ranking profile. SourceQuality validates its weighted score and observed feature weight.
Proposition retains exact evidence-relative spans and all numeric comparison dimensions; Comparison
records its endpoints, shared questions, unit conversion and rationale. Both are deterministically
rechecked against evidence during state validation. ResearchGap gains a validated query purpose.

State adds overwrite projections source_quality, propositions, comparisons, analysis_signature,
last_analysis_pass, analysis_notes and analysis_limited. Fresh initialization clears them. Numeric
conflicts or a truncated comparison set prevent sufficient coverage. SynthesisInput includes ranking
and comparison context. Exact-quote audits and opposing proposition links retain distinct semantics.

EvidenceGraph verifies unique node/edge IDs and known endpoints. project() builds it from validated
state and optionally selects a claim neighborhood. audit() retains feature and judgment records.
The graph-version 6 profile refuses earlier workflow registrations. See PHASE6.md for supported
sentence forms, grouping, scope/date/unit rules, exports and limits.
