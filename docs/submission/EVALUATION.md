# Evaluation summary for submission

These values are copied from the measured Phase 9 audit, not new experiments.
The full protocol and repairs are in [PHASE9_REPORT.md](../evaluation/PHASE9_REPORT.md).
Labels remain a Codex draft requiring independent human review. The saved-answer
review dimensions are defined in [V2_SEMANTIC_RUBRIC.md](../evaluation/V2_SEMANTIC_RUBRIC.md).

## Corrected v2 comparison status — 6 October 2026

The corrected dataset is `docs/evaluation/dataset_v2.json` (SHA-256
`36dce5628b62dce34e5d5543839f6995c581f6b11121fdc38811c9ddbec092f7`). It keeps
the synthetic corpus frozen and narrows the first 16 questions to the stated
passage factors. The offline matched runner completed 40 rows: 20 controlled
single-response baselines and 20 one-pass workflows. It used zero provider calls;
36 rows completed, two ended partial and two ended insufficient-evidence under
the fixture's bounded evidence rules. These outcomes verify protocol and replay
mechanics only, not source truth or model quality.

The user approved up to 140 Gemini calls for the same comparison. The paid run
was prepared with a durable global cap but did not start: the environment
approval service rejected the network command after exhausting its review
credits. No new Gemini call ran, and the historical 26/30 and 28/40 ledgers were
not modified. The configured model remains `gemini-3.5-flash-lite`.

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

## Historical pre-v2 sign-off checklist

1. A person reviews all 20 annotations using [the packet](../evaluation/ANNOTATION_PACKET.md)
   and records decisions, name, date and dataset hash.
2. Preserve a reviewed dataset version and freeze settings before reruns.
3. Improve question/corpus scope in a new frozen version before meaningful quality reruns.
4. Interpret actual provider outcomes, including partial/failed runs and known denominators.

The checklist above describes the original v1 freeze. The corrected v2 offline
protocol and its blocked paid execution are recorded near the top of this file;
the independent human review gate remains open.

The authorized extension and repair checks have now executed, as recorded below.
Original provider failures and draft labels remain preserved.

## Authorized extension and repair — 4 October 2026

The historical table above is preserved. User delegation subsequently authorized
up to 40 additional calls. The extension recovered all eight missing one-shots;
combined with the prior 12, there are now **20/20 usable responses**. All successful
one-shot receipts have 3,041 known tokens in total; historical latency for the
first 12 remains unknown. These responses are ungrounded general-knowledge
baselines: usable JSON does not establish correct facts or verified citations.

| New execution | Calls | Actual outcome |
|---|---:|---|
| Missing one-shots, cases 01–08 | 8 | Eight usable responses; 1,261 known tokens |
| Original extension development workflow, case 01 | 4 | insufficient_evidence/no_evidence; two passes, zero claims |
| Original extension held-out workflow, case 13 | 5 | partial/fatal_error; one pass, one cited claim; coverage response failed validation |
| Coverage/schema diagnostic and experimental planning | 2 | Coverage validated; planning returned HTTP 400; noncoverage bounds reverted |
| Fresh repaired workflow, case 14 | 9 | All nine stages succeeded; partial/pass_limit; three passes and two cited claims; 14,587 known tokens |

Shared allowance: **28/40** reserved, 27 HTTP 200 and one HTTP 400; 26 schema-valid
responses, 29,641 known tokens and one unknown usage. Dollar cost remains N/A.
The original ledger is unchanged at 26/30. All new full workflows used the fixture
full variant's three-pass/12-call/eight-search limits. Original measured outcomes
remain frozen; the diagnostic's changed source/case is separately recorded.

The broad synthetic comparison questions often invite criteria absent from their
two dependency statements. Codex reviewed all 20 labels and recorded these
qualifications in [AI_REVIEW.md](../evaluation/AI_REVIEW.md); no human validation
or provider superiority is claimed. Case 14's exact quotation coverage is 1.0,
while its broader planner criteria remain unmet, yielding an honest partial report.
See [the complete extension report](../evaluation/EXTENSION_REPORT.md).
