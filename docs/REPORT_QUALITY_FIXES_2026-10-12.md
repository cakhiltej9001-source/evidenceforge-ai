# Remaining report quality fixes - 12 October 2026

## Implemented

New research runs use quote-selection contract version 5. Earlier saved contracts
keep their registered behavior; they do not silently migrate or repeat provider calls.

1. Detect ambiguous flattened numeric rows with repeated adjacent values and
   percentages. Exclude those passages instead of guessing column associations.
   Existing delimited rows are not reconstructed by this heuristic.
2. Separate numbered Problem/Question/Exercise sections from preceding prose using
   exact snapshot offsets. Exclude whole exercise blocks, including their answers,
   rather than admitting unrelated worksheet instructions.
3. Apply a second check to audited report quotations. Exact text support does not
   authorize ambiguous table interpretation or exercise content as a finding.
4. If a criterion asks for missing/unreported data, require an explicit absence
   statement in the final question-linked quotations. Otherwise record an unmet
   criterion and return a partial/insufficient result, even if the model said
   sufficient and the critic approved.
5. Disclose the conservative rules and unresolved criteria in Markdown/JSON exports.

These are bounded text heuristics, not a general semantic evaluator. They may
exclude useful worksheet material. They do not reconstruct lost table layout,
prove a complete per-entity missing-data inventory, or establish source truth.
Broader table-aware extraction and independently reviewed quality evaluation
remain extensions.

## Verification

Seven new adversarial regressions cover flattened tables, useful prose,
delimited rows, complete exercise blocks, legacy behavior, misleading numerical
coverage, explicit missing-data reporting, and finalizer rejection of exact but
ambiguous quotations. The local strict mypy gate passed for all 85 source files;
Ruff lint/format also passed.

An offline replay applied the new finalizer policy to the saved NASA report
run_808ad22fe80546f8bbc9d534b2397973. It omitted both problematic claims and changed
the replay outcome to insufficient_evidence with three explicit quality gaps.
The original historical report/state was preserved byte for byte. Provider
receipts were unchanged. Network access was blocked: zero attempts, zero new
Gemini, Tavily or LangSmith calls.

Private replay evidence is saved under:
.evidenceforge/verification/report-quality-2026-10-12/.
The replay is not a fresh provider workflow. The earlier six-role Gemini,
one-search Tavily and synthetic LangSmith verification remains historical proof
of provider execution.

Source commit: 0777791. [Full CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38242786448)
passed both Python and Docker jobs: 489 tests in 38.57 seconds, Ruff, strict mypy,
package build, Render schema, deployment smoke, persistence, backup/restore and
authenticated gateway checks. See [current phase status](FINAL_STATUS_2026-10-12.md).

## Remaining external or deferred work

- Independent human benchmark review and independent OCR accuracy review require
  an independent person; AI work is not labeled human sign-off.
- Broader real-source semantic quality and general table reconstruction remain
  optional evaluation/development.
- Hosting remains free only (INR 0/month), with temporary public fixture storage
  and durable local research. Hosted durable storage/background jobs are deferred.
