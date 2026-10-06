# Corrected Gemini comparison — 6 October 2026

## Protocol and identities

Twenty frozen synthetic cases each received a controlled single-response baseline
and a one-pass production workflow. Both variants received the complete same
corpus, with no live web search and no prior-report memory. The first 16 questions
ask only for the factors stated by the supplied passages. Cases 17–18 concern
scoped numeric disagreement; cases 19–20 have no sources.

- Model: `gemini-3.5-flash-lite`, the configured authorized fallback.
- Runtime source: `0f070d134491e2b2a161ecdfdaf987daec2ac904`.
- Dataset SHA-256:
  `36dce5628b62dce34e5d5543839f6995c581f6b11121fdc38811c9ddbec092f7`.
- Saved manifest source hashes matched the unchanged local source after execution.
- Saved outputs/receipts: `.evidenceforge/evaluation/phase9_v2_gemini/`.
- [AI review](V2_AI_REVIEW_2026-10-06.json) records the result hash and all 40 rows
  against the [six-dimension rubric](V2_SEMANTIC_RUBRIC.md).

The user approved a separate 140-call cap. Execution reserved **136 calls**, all
HTTP 200, all locally validated, with no automatic retry. The old ledgers remain
unchanged at 26/30 and 28/40. No paid call was made for the subsequent AI review.

## Measured outcomes

| Measure | Single response | Workflow |
|---|---:|---:|
| Saved cases | 20 | 20 |
| Provider calls | 20 | 116 |
| Completed status | 20 | 16 |
| Partial conflict reports | 0 | 2 |
| Insufficient-evidence status | 0 | 2 |
| Correct abstention with no claims, empty cases | 2/2 | 2/2 |
| Dispute flag, conflicting cases | 2/2 | 2/2 |
| Both stated factors retained, factor cases | 16/16 | 16/16 |
| Known input tokens | 3,975 | 124,501 |
| Known output tokens including thinking | 1,317 | 15,294 |
| Known total tokens | 5,292 | 139,795 |
| Mean wall-clock latency per case | 6.852 s | 31.106 s |

The baseline's completed status includes its two explicit abstentions; the
workflow distinguishes insufficient evidence. Status labels alone are not quality
scores. Workflow case 17 stopped at `model_call_limit`; case 18 at `pass_limit`.
Both retain the conflicting 100/120 GWh values and disclose unresolved work.
Dollar cost remains N/A because no verified pricing policy was applied.

Usage above comes from the recorded provider observations. The workflow's legacy
aggregate scoring fields report token usage as unknown; those fields are preserved
and were not substituted for the observations. All 136 observation records contain
known usage. Latencies include local processing and provider/network delay; no
randomized repeated latency experiment was performed.

## Review and interpretation

Every baseline source ID belongs to its supplied corpus and supports its quoted
substring. Workflow evidence IDs exist in retained state; completed claim audits
verify source quotation support. No reviewed factual claim introduces a value or
factor absent from the supplied corpus. This establishes retained-text support,
not real-world source truth.

All 16 baselines preserve both stated factors while omitting `Synthetic fixture:`.
Cases 03, 06, 09, 10, 12, 13, 15 and 16 also omit the final period. The raw strict
reference-coverage metric penalizes those omissions. Reviewing the same factors
without that label/final punctuation gives 16/16 coverage for both approaches.
All 16 baseline rows need revision under the rubric's complete-sentence quotation
rule. The baseline prompt permits a supported minimal quoted span, so this stricter
rubric difference must not be presented as a measured factual-quality advantage.

The workflow's quotations preserve full sentences and provide inspectable
snapshots, receipts, locators and unresolved conflict records. This uses more calls
and tokens. The one-response baseline is faster and cheaper by the measured usage.
No price estimate or general provider-outperformance claim is inferred.

Workflow case 18 preserves the requested 2024 disagreement but its planner invents
monthly totals/variance criteria. The report exposes these as unmet; its scope
dimension is **revise**, while supported quotations and conflict handling pass.
Plan approval and displayed gaps remain necessary controls; exact citation audits
do not detect all planning-scope errors. The saved answer is not rewritten after
measurement and no extra paid rerun was made.

This was a delegated **Codex AI review**, with no independent human attestation.
The small synthetic corpus and previously inspected partitions do not support a
blind held-out or general research-accuracy claim. Earlier dataset/paid failures
remain preserved in [the original report](PHASE9_REPORT.md) and
[extension record](EXTENSION_REPORT.md).
