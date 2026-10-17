# Report presentation and selection repair — 18 October 2026

App version: **2026-10-18.1**. New workbench runs use production policy 5.

## Observed problem

A completed live research export passed 13 quotation audits but its highlighted
answer remained vague. Findings included course promotions, transcript timestamps,
flattened table markup, adjacent job-role material and future-year wording.
Workflow completion and exact citation support did not establish editorial quality
or independent source truth.

## Repair

- Rank how-to answers using the approved criteria and concrete content, with up to
  five complementary exact excerpts. Numbering is for reading, not a verified timeline.
- Exclude promotional/transcript clutter and tables from the concise answer.
- For cluttered findings, show clean exact sentences only when their context can
  be preserved. Otherwise retain the quotation in saved sources and JSON rather
  than highlighting it. No sentence is rewritten and no table values are inferred.
- Preserve caveats by keeping the whole quotation or abstaining. Do not remove a
  future-year or adjacent-role context to make an excerpt appear applicable.
- Warn about future-year wording relative to the saved run year, unless the user
  explicitly requested that year. Properly aligned tables retain their existing
  display path; malformed layout is not guessed.
- New Gemini selection/review guidance prioritizes concrete, complementary evidence
  and rejects advertisements, transcript filler, metadata and adjacent-role drift
  when they prevent answering the approved criteria. A persisted reference date
  supplies the temporal context.
- Policies 0–4 keep their historical prompt behavior and omit the new date field.
  Saved-run resume stays bound to its original policy. A fresh explicit retry uses
  the current policy without resetting historical provider ledgers.

## Offline evidence

The supplied completed export was replayed locally for presentation only:

| Check | Result |
|---|---|
| Original retained passages / audited quotations | 38 / 13 |
| Concise exact excerpts | 5 |
| Cluttered or out-of-scope quotations not highlighted | 8 |
| New provider calls / source fetches | 0 / 0 |
| Original user export | Unchanged |

The question and date were taken from the accompanying PDF because export v1 does
not contain the original request or run timestamp. This was a presentation replay,
not a reconstructed authentic checkpoint or a fresh citation/source verification.
Private exports, source text and replay artifacts were not added to this repository.

## Limits

These are bounded lexical presentation checks, not a semantic truth verifier or
a complete editor. Future-year and job-role checks are conservative heuristics.
The display filter does not recompute research coverage or upgrade/downgrade a
historical run status. An omission notice keeps that distinction visible.

New guidance cannot manufacture missing evidence. A report may still need more
research, human review or a better source set before final project submission.
The changed policy has not been verified with a new paid live run in this repair.
Free hosting and the existing per-run API budgets remain unchanged.

## Verification

Local lint and formatting gates passed. Strict mypy passed all 90 source files.
Focused regression verification and full GitHub CI are recorded after completion;
no new provider allowance was consumed by these checks.
