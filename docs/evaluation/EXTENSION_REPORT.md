# Authorized Gemini extension and repair results

Recorded 4 October 2026, Asia/Calcutta. The user delegated execution after the
explicit 40-additional-call/private-GitHub request; automatic approval review
accepted both actions. Model: `gemini-3.5-flash-lite`.

## Counts and limits

- Original ledger: **26/30**, unchanged.
- Shared extension/repair ledger: **28/40**, leaving 12 unused.
- HTTP outcomes: 27 HTTP 200 and one HTTP 400; 26 locally validated responses.
- Known input tokens: 24,224; known output including thinking: 5,417; total 29,641.
- One call has unknown usage. Dollar cost is N/A without a verified pricing policy.
- Eight recovered one-shots plus the prior 12 give **20/20 usable responses**.
  Their combined known usage is 3,041 tokens, including 1,261 for the new eight.
  Responses have no retained-source grounding score; usable JSON is not truth.

The original extension invocation's results remain unchanged at 17 calls. The
coverage experiment (two calls) and final workflow (nine calls) have their own
manifests/results and use the same 40-call ledger. No allowance was reset or
failed request automatically retried. No further paid execution is needed to
verify this repair.

## Preserved outcomes

| Execution | Case | Calls | Passes | Claims | Status / stop |
|---|---|---:|---:|---:|---|
| Recovered one-shots | diverse_01–08 | 8 | N/A | N/A | Eight usable responses |
| Original extension development workflow | diverse_01 | 4 | 2 | 0 | insufficient_evidence / no_evidence |
| Original extension held-out workflow | diverse_13 | 5 | 1 | 1 | partial / fatal_error |
| Coverage diagnostic | retained diverse_13 evidence | 1 | N/A | N/A | Coverage schema and question/evidence references validated |
| Broad schema experiment | diverse_13 | 1 | 0 | 0 | failed / fatal_error; planner HTTP 400 |
| Final repaired workflow | diverse_14 | 9 | 3 | 2 | partial / pass_limit; all model stages succeeded |

All full workflow invocations used the same three-pass, 12-model-call,
eight-search limits as the fixture full variant. Their realized work differs.
The development planner asked for quantitative/common-scope criteria absent from
the two short dependency passages; lexical admission yielded no evidence. The
original held-out coverage response failed local validation. Its body was not
retained, so its exact failing field cannot be established retrospectively.

The coverage instructions now require evidence IDs for every included criterion
and omit unsupported criteria. Wire schemas retain array bounds only for coverage;
the planning experiment returned HTTP 400, so other roles retain the previously
working schema normalization. Local validation still checks the complete contracts.
Failures now retain only error kinds and allowlisted field locations, excluding
response values and unknown field names. A regression verifies this redaction.

The final workflow (`run_481873c1058c4d938bf8ff10253e6a00`) made nine successful calls
and used 14,587 known tokens in 30.1193 seconds. Three coverage stages, synthesis
and critic all succeeded. Two retained quotations passed citation checks;
exact reference-aspect coverage was 1.0. Its broader planner criteria remained
unmet, so it correctly ended partial at the pass limit. Those string/citation
scores establish retained-text support, not factual accuracy or complete coverage
of the broader question.

## Review and interpretation

Codex reviewed all 20 cases on the user's behalf, recorded individually in
[AI_REVIEW.md](AI_REVIEW.md) and [AI_REVIEW.json](AI_REVIEW.json). Sixteen broad
output questions have only qualitative dependency evidence. The two scoped
numeric disputes and two empty-source abstention labels are consistent with
fixtures. Human validation is not claimed and the dataset remains a draft.

This was a repair investigation using already inspected cases; its final case is
a post-repair diagnostic, not an untouched held-out research-quality result.
The general-knowledge one-shot baseline has different evidence access from the
corpus-bound agent. No superiority or general factual-quality claim follows.
A stronger benchmark needs reviewed, narrower questions or richer frozen corpora,
a versioned dataset and comparisons with a stated common evidence/scoring policy.

## Reproducibility and retained evidence

Dataset SHA-256:
`5e5c012fd1a612513a934e30469ba5a20b532e909732cfd47500f8453cdf4e89`.

| Record | Local ignored path |
|---|---|
| Original benchmark | `.evidenceforge/evaluation/phase9_diverse/` |
| Extension manifest/results and shared ledger | `.evidenceforge/evaluation/phase9_extension/` |
| Coverage/planning experiment | `.evidenceforge/evaluation/phase9_extension_repair/` |
| Final workflow manifest/result/report/audit | `.evidenceforge/evaluation/phase9_workflow_repair/` |
| Aggregated ledger/usage summary | `.evidenceforge/verification/pending-fix/gemini-final-summary.json` |

Original adapter SHA-256 was
`fa6a51927d40eec1cd1a2bc15cff7a296f2082d67d26709823f8abc0995a8700`.
Final repaired adapter SHA-256 was
`63ceda29878a6e14e03e63c0941bd2056d378761023f068e95c4e273b88bc358`.
Source hashes and budgets are frozen per invocation. Changed source cannot
silently replay the original extension. Runtime receipts, payloads, checkpoints
and secrets remain excluded from Git and Docker uploads.

The two verification scripts default to read-only dry runs. Their `--execute`
mode is explicit, checks remaining shared allowance and refuses to overwrite an
existing result. They send fixture question/evidence payloads to Google and may
incur cost; use the recorded results for this completed investigation.
