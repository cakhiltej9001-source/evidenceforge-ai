# Evaluation summary for submission

These values are copied from the measured Phase 9 audit, not new experiments.
The full protocol and repairs are in [PHASE9_REPORT.md](../evaluation/PHASE9_REPORT.md).
Labels remain a Codex draft requiring independent human review.

## Synthetic comparison

20 frozen cases: 12 development and 8 held out. Sixteen compare two synthetic
passages, two concern disputes and two have empty corpora. One-pass and full-agent
variants share the same frozen passages and scripted model. The measured ablation
changes maximum retrieval passes from one to three; maximum model calls are 12
and searches eight. All 40 variants ran; missing runs are zero.

| Partition | Variant | Cases | Completed | Noncompleted | Exact aspect coverage | Mean latency |
|---|---|---:|---:|---:|---:|---:|
| Development | One pass | 12 | 0 | 12 | 0.5000 | 8.4084 s |
| Development | Full agent | 12 | 12 | 0 | 1.0000 | 10.0108 s |
| Held out | One pass | 8 | 0 | 8 | 0.6667 | 7.4996 s |
| Held out | Full agent | 8 | 4 | 4 | 1.0000 | 9.8227 s |

Noncompleted includes partial, insufficient and failed states, not missing runs.
Exact aspect coverage can be 1.0 when a dispute prevents a completed report.
Conditional citation precision/coverage and groundedness against admitted evidence
were 1.0 where denominators were defined. Tiny held-out dispute and abstention
checks scored 1.0; undefined denominators are N/A. These are retained-string/
workflow checks and do not establish general factual accuracy or source truth.
Ranking, contradiction and repair have component tests but no separate measured
Phase 9 ablations; no quantitative benefit is claimed for those components.

Dataset SHA-256: `5e5c012fd1a612513a934e30469ba5a20b532e909732cfd47500f8453cdf4e89`.
Original freeze and repair amendments remain preserved with the ignored run data.

## Gemini baseline and diagnostic probes

| Measurement | Actual recorded outcome |
|---|---|
| Global allowance | 26 reserved of the authorized 30 calls |
| HTTP outcomes | 23 HTTP 200, two HTTP 429, one unconfirmed request |
| Usable one-shot cases | 12/20; eight earlier cases failed/remained unconfirmed |
| Known one-shot tokens | 1,780 across 12 exact-request-hash matched successful receipts |
| Development workflow probe | Partial/fatal_error; five calls, 2,479 known tokens and one unknown usage |
| Held-out workflow probe | Failed/fatal_error; one call, usage unknown |
| One-shot citation/groundedness/aspect quality | N/A: no source-grounded scoring or verified citations |
| Historical one-shot latency | N/A: not captured |
| Dollar cost | N/A: verified pricing policy unavailable |

The model was `gemini-3.5-flash-lite`. HTTP 200 is not equivalent to a usable
validated response. Seven early HTTP 200 responses failed local handling; their
bodies were not retained, so exact individual causes are unproven. A compressed
response defect was repaired and tested; records were not silently replayed.

The two workflow probes used one subquestion/two passes/eight model calls,
compared with the fixture full variant's three passes/12 calls. They are incomplete
diagnostic probes, not a matched quality comparison. No claim that Gemini or
EvidenceForge outperforms another model is supported by these measurements.

## What remains before benchmark sign-off

1. A person reviews all 20 annotations using [the packet](../evaluation/ANNOTATION_PACKET.md)
   and records decisions, name, date and dataset hash.
2. Preserve a reviewed dataset version and freeze settings before reruns.
3. Obtain explicit authorization for the prepared additional Gemini allowance;
   no new paid calls were authorized merely by proceeding to Phase 11.
4. Complete provider-available matched runs, disclose failures/usage and interpret
   quality using human-reviewed evidence and known denominators.

The proposed extension has not executed. The current dataset and provider limits
remain visible rather than being replaced with assumed passing results.
