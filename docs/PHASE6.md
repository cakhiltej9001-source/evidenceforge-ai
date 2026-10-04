# Phase 6: evidence graph, ranking and scoped disputes

Implemented 1 October 2026. This phase adds deterministic evidence analysis to the existing offline
research graph. It uses no new dependencies or live provider calls. Verification results are in PROGRESS.md.

## Execution steps and time estimate

The initial estimate was 45-90 minutes including implementation, tests and documentation. This was
an estimate for this development task, not a research-run deadline. The work follows these steps:

1. Read the milestone, state contracts, retrieval admission, quality loop and persistence profile.
2. Add validated ranking features, scoped numeric propositions, comparisons and graph records.
3. Rank sources with explicit weights, unknown values, supplied metadata rationale and copy groups.
4. Insert evidence_intelligence between extraction and coverage; replace projections each pass.
5. Mark comparable conflicts disputed and queue primary-source/counter-evidence queries through
   the existing pass/search/evidence/time limits. Preserve both passages when no resolution exists.
6. Order synthesis evidence by ranking, retain opposing links during citation checks, and export
   graph.json, audit.json and inspection.md alongside report.md and state.json.
7. Verify numeric/date/unit/population/condition/noncomparable cases, copied families, unknown
   metadata, graph references, tampering, analysis caps, search limits and checkpoint resume.
8. Run the full offline regression, lint, formatting, strict types, installed CLI and package gates.

## Run the synthetic dispute demo

Run in PowerShell from the project directory:

```powershell
cd "C:\Users\AKHILTEJ\Documents\ChatGPT\AI Research agent"
uv sync --locked
uv run --locked evidenceforge-research "What was Northfield solar electricity output?" --demo dispute --data-dir .evidenceforge/phase6-demo
```

All publishers and measurements in this demo are synthetic. The first pass retains 100 GWh and
120 GWh for the same 2024 scope. The next pass adds a 100000 MWh equivalent, a 900 GWh statement
for 2023, and a copied source. The two 2024 values remain disputed; the workflow keeps both and
returns a partial report. A newer or more numerous source does not decide which value is true.
The 2023 statement is not comparable to the 2024 scope. Unit conversion equates 100 GWh and
100000 MWh. The copied statement contributes no independent vote.

The command prints absolute paths to five files in reports/<run_id>:

| File | Contents |
|---|---|
| report.md | Audited quotations, comparison details, unresolved gaps and stop reason |
| state.json | Validated workflow state, including versioned analysis projections |
| graph.json | Questions, final claims, exact evidence, sources, edges and gaps |
| audit.json | Proposition spans, numeric judgments, ranking features, links and citation audits |
| inspection.md | Accessible record/relationship/ranking tables with retained locations |

Use the printed state.json path to inspect all records:

```powershell
uv run --locked evidenceforge-inspect "ABSOLUTE_STATE_JSON_PATH"
uv run --locked evidenceforge-inspect "ABSOLUTE_STATE_JSON_PATH" --claim CLAIM_ID
uv run --locked evidenceforge-inspect "ABSOLUTE_STATE_JSON_PATH" --claim CLAIM_ID --format json
```

Copy a claim ID from inspection.md or graph.json. The selected view includes the finding's recorded
passages, compared passages, source locators, question links and gaps. Unknown claims and dangling
references are rejected. For another local owner, pass the same --owner used by research. This is a
local scope consistency check; it is not account authentication. An interactive UI remains Phase 8.

## Explainable source ranking

The version is weighted_metadata_v1. Research accepts --ranking-profile general/current/historical;
the default is general. The profile is explicit and recorded in the resume configuration.

| Feature | General | Current | Historical |
|---|---:|---:|---:|
| Admitted lexical relevance | .35 | .30 | .40 |
| Supplied primary evidence | .25 | .25 | .25 |
| Supplied publisher identity | .10 | .08 | .10 |
| Supplied methodology transparency | .10 | .10 | .10 |
| Publication recency | .05 | .12 | .00 |
| Independent comparable agreement | .10 | .10 | .10 |
| Source family uniqueness | .05 | .05 | .05 |

Each feature stores a value or null, weight and rationale. Missing metadata stays null and contributes
an explicit neutral 0.5 in the weighted sum. observed_weight records how much weight has known
values; neither number is a confidence or truth probability. Presence of a publisher name is a
supplied identity signal, not authenticated authority. Primary/methodology hints require a rationale;
no government/academic hostname is automatically promoted. The current Tavily adapter does not
invent these hints. The primary-versus-newer-secondary test exercises an authored metadata case.

Recency uses a valid nonfuture ISO publication date relative to the run start, with a linear ten-year
decay. This is a baseline policy, not a measured optimum. Historical profile assigns it zero weight.
Sources are grouped transitively by supplied source_family or identical retained-content SHA-256.
Default web family labels use the host; document chunks share their document family. These are
conservative grouping signals, not proof of independence. Identical normalized proposition quotes
are also labeled duplicate and excluded from independent comparable agreement. Adding a copy with
an earlier record ID does not change the group's content-derived identity.

Rankings order evidence supplied to synthesis. They do not discard opposing evidence or resolve a
conflict. Tune weights only against development judgments; no ranking improvement is claimed.

## Comparable numeric propositions

scoped_numeric_v1 is a deliberately narrow deterministic extractor. Its recognized sentence form is:

```text
Northfield solar electricity output was 100 GWh in 2024 for all plants under standard operation.
```

Every proposition retains evidence ID, exact relative character span, quote, entity, metric, timeframe,
population, conditions, decimal value and unit. Fields are re-derived during state validation; changing
a number or relationship in a checkpoint is rejected. Dates must be valid years or ISO calendar dates.
Supported metric phrases: electricity output, energy output, installed capacity, capacity factor.
Units: Wh/kWh/MWh/GWh/TWh, W/kW/MW/GW and percent. Unit symbols require exact SI casing;
unsupported decimal conditions remain unclassified. Energy, power and percent are distinct dimensions.

Propositions compare only when they share a research question. Different entity, metric, timeframe,
population, conditions or unit dimension means not_comparable, with a reason. Publication dates
support ranking; they are not substituted for measurement timeframes. Exact equal converted values
support numerical agreement; unequal values under identical explicit scopes create an unresolved
contradiction. Decimal arithmetic uses exact equality; uncertain rounding/error intervals are not
modeled. Free prose, unknown scopes, qualitative negation and unsupported sentence forms remain
unclassified. No absence-of-support or source-count rule creates a contradiction.

Default caps are 128 propositions and 2000 comparisons, configurable through ResearchOptions.
Reaching a cap discloses incomplete analysis and prevents sufficient/completed status. These caps
bound analysis after already bounded evidence retrieval. Unclassified prose is reported as such;
a completed fixture run does not establish exhaustive semantic contradiction detection.

## Routing, citation semantics and persistence

```text
Source Processor -> Evidence Extractor -> Evidence Intelligence -> Coverage Evaluator
                                                               -> budgeted queries or synthesis
```

Unresolved comparisons override lexical sufficiency for their shared questions. Structured gaps carry
primary_source or counter_evidence purpose; Query Generator uses existing source availability, query
deduplication and allowances. Additional queries may leave the conflict unresolved. Repeated retained
text does not improve the coverage progress signature. Bounded stop yields partial output with gaps.

Synthesis receives the ranking and comparison records. The fixture keeps conflicting quotations in
the disagreements section. Citation checks authenticate exact retained quotes. Separate contradicts
links express conflicting numeric content; they do not claim that a quotation was fabricated. Both
passages stay in the evidence registry, graph, audit and comparison report even if synthesis cites only
one. Unsupported claims remain omitted using the existing citation-repair logic.

Graph edges are addresses, supports, contradicts, contextualizes, uncertain, retrieved_from and
duplicate_of. Each endpoint resolves to an authoritative state record. Link/comparison edges include
record_id for their stored judgment. Comparison audits retain date/scope explanations. A source-family
edge means common family or retained content, not proof that two entire publications are duplicates.
JSON contains private document passages when used locally; exports stay in ignored local data.

The resume profile advances to graph_version 6. Earlier Phase 5 registrations are refused rather than
silently executed against changed graph routing. Their exported reports remain readable. New Phase 6
runs can pause/resume using the existing CLI boundaries, and terminal resume redelivers the same
projections. Files are individually atomic; the five-file delivery is not one transaction.

## Verification and remaining scope

All fixtures are synthetic and offline. tests/test_evidence_intelligence.py checks disagreement,
unit equivalence, date/entity/metric/population/condition/dimension mismatches, missing scopes,
invalid dates, copy families, recency/primary ranking, unknown features, caps, graph selection,
source/quote/judgment tampering, search limits and checkpoint redelivery. The full regression includes
the earlier actual separate-process restart case. Exact gate results are recorded in PROGRESS.md.
No human-labeled benchmark, broad semantic model comparison, cost improvement, live research or
research accuracy result is claimed. Phase 7 is the next milestone when authorized.

## Saved example

The actual installed demo output is preserved as public synthetic artifacts in
[examples/phase6](examples/phase6/README.md), including report, state, full/selected graphs,
audit and accessible inspection table. The audit records 3 numeric contradictions, 2 agreements,
1 duplicate and 4 scope differences. The selected finding view has 12 nodes and 24 edges.
These are fixture record counts, not benchmark results.
