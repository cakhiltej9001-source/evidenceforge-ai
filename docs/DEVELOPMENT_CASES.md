# Development cases

These are development acceptance specifications, not a held-out benchmark or measured results.
The synthetic public Phase 1 test passage is explicitly labeled as synthetic. Tests reject ordinary
network connections (stdlib socketpair setup is allowed for Windows asyncio), and configuration tests use fabricated keys only.

| Case | Phase | Expected behavior |
|---|---|---|
| Invalid/blank question or impossible limits | 1 | Validation failure before research; booleans do not become counts |
| Bad record ID, locator, extra field or naive timestamp | 1 | Record rejected; no silent schema repair |
| Same immutable ID replayed/conflicting payload | 1 | Replay no-op; conflict fails; input state unchanged |
| Same evidence acquired again | 1 | Preserve all provenance associations without changing passage |
| Call/reservation lifecycle replay | 1 | No rollback, response replacement or double settlement |
| Unknown usage/cost | 1 | Null retained; known estimate references a price-table version |
| Owner mismatch/dangling source/snapshot/reference | 1 | Complete snapshot rejected |
| Stale draft audit or unplaced report statement | 1 | Snapshot rejected until current claim registry/audit aligned |
| Fresh run after earlier state | 1 | New identities/counters/containers; no evidence or approvals inherited |
| JSON and checkpoint serialization | 1 | Actual installed LangGraph serializer restores equivalent JSON state |
| Config environment/dotenv precedence | 1 | Explicit env wins; blank keys remain unconfigured; diagnostics redacted |
| Planner/context join once; malformed planning output | 2 | Both branches finish; one query-generation activation; typed failure |
| Stable plan/query IDs and fresh planning run | 2 | Ordering-independent question IDs; owner isolation; new run/thread IDs |
| Malformed/oversized/invalid UTF-8 plan/query response | 2 | Fixed schema error; raw output absent from diagnostics |
| Cross-owner/unrequested/disabled/duplicate/excess context | 2 | Context discarded; no query model call |
| Missing or unavailable optional context | 2 | Disclosed unavailability; usable web queries continue |
| Query normalization and attempted keys | 2 | Association union; attempted candidates skipped; pending is not attempted |
| Query pass/search/source allowances | 2 | Bounds include reserved/settled searches; released capacity excluded |
| Offline CLI and configured live model | 2 | Explicit fixture marker; no silent fallback from live configuration |
| Empty/failed/duplicate retrieval | 3 | Provenance/rejection/errors retained within timeout/count limits |
| Missing aspect versus immediate sufficiency | 4 | Targeted second pass versus no additional search |
| No admissible evidence | 4 | Honest insufficient-evidence result without invented answer |
| Unrelated citation/numeric or date qualifier | 4 | Audit rejects unsupported attribution and repairs within allowance |
| Critic/audit exhaustion | 4 | Supported partial report with recorded reason; all loops stop |
| Scoped documents and process restart | 5 | Located citations; isolated owners; completed calls reused |
| Real/apparent/date/unit/unrelated contradictions | 6 | Comparable disputes only; follow-up shares existing budget |
| Cancellation/rate limit/budget race/injection | 7 | Bounded failure, redacted events, no privilege escalation |
| Approval edits/reconnect | 8 | Correct resume; no duplicate paid side effects |
| Fixed snapshots and common human reference labels | 9 | Fair baseline comparisons with frozen settings and untouched test set |

Tune prompts/chunks/ranking/thresholds on development cases only. Held-out questions/labels remain
outside runtime memory. Final benchmark metrics require actual annotated runs; no accuracy,
groundedness or cost improvement is claimed by these case definitions.


Implemented acceptance checks through Phase 3: 183 passing tests on the locked Windows/Python 3.12
environment. The Phase 2 test files are test_planning.py, test_planning_context.py and
test_planning_queries.py. This is workflow verification, not a research-quality benchmark.

Phase 3 implemented cases in test_retrieval.py/test_tavily.py/test_retrieval_storage.py cover exact
spans, duplicate provenance, response reuse, empty/failed search, scope rejection, bounded sizes,
evidence/elapsed/search limits, concurrent reservations, cancellation ambiguity, immutable usage,
corrupt artifacts and mocked Tavily request/response behavior. These are offline workflow checks.

## Phase 4 executable cases

`tests/test_research.py` executes immediate and genuine second-pass retrieval, empty evidence,
shared critic/citation rewrites, failed support repair, malformed/unknown references, pass-limited
partial output, recursion/capacity bounds, date qualifiers, uncited recommendations, corrupt snapshots
and output-write failure. All inputs are synthetic and ordinary network connections remain blocked.
These are behavioral workflow checks, not an accuracy benchmark.

## Phase 5 executable cases

`tests/test_documents_persistence.py` generates public/synthetic TXT, PDF and DOCX input and checks
located cited reports, mixed/textless/encrypted PDF behavior, unsupported/malformed/oversized files,
exact overlap and hashes, owner/request filtering, corruption and locator tampering, separate report
memory, fresh terminal-state reset, configuration/foreign-thread rejection, single-writer locks,
thread isolation, changed originals after retrieval and actual subprocess restart/resume.

## Phase 6 executable cases

`tests/test_evidence_intelligence.py` exercises comparable conflicting numbers, equivalent units,
different timeframes/entities/metrics/populations/conditions/unit dimensions, unknown prose and
invalid dates. It checks a relevant primary source against a newer secondary source, unknown/future
metadata, conservative copy grouping and stable copy identity, exact proposition spans, tampered
numbers/judgments, graph links and selected findings, analysis caps, bounded targeted searches,
consistent evidence without extra counter-evidence calls, and resume/redelivery. All measurements
and publishers are authored synthetic fixtures. These cases verify mechanics, not measured quality.


## Input and configuration audit cases

tests/test_guardrails.py verifies schema rejection without raw-input disclosure, clarification
before model/search calls, topic preservation, no run registration for vague input, and private
dotenv isolation in default tests. This is an explicit limited input policy, not a held-out
semantic classifier evaluation. Phase 0-7 audit evidence is in PHASE0_7_VERIFICATION.md.
