# Distinct retained corpora check - 8 October 2026

The [sanitized measurement](RETAINED_CORPORA_2026-10-08.json) replays the same solar
and wind question against two existing, unchanged sets of public snapshots.
Snapshot hashes are disjoint. No search or live model calls were made.

| Retained corpus | Content scope | Sources | Claims / exact locators | Outcome | Gaps |
|---|---|---:|---:|---|---:|
| EIA and Utility Dive | Full text | 5 | 30 / 30 | completed / sufficient | 0 |
| Wikipedia fallback | Search excerpts | 5 | 9 / 9 | partial / pass_limit | 1 |

Citation precision against retained text and citation coverage were 1.0 in both
cases. All nine checks passed, including exact locators, separate snapshot sets,
preserved source access scope and no evidence borrowed from the other corpus.
Measured local replay times were 5.8845 and 7.7114 seconds; these are not live LLM
latencies. Provider calls: **0**.

## Concrete negative control

The Wikipedia excerpts contain no whole-word wind evidence. Their one substring
occurrence is inside “unwinding”. The production tokenizer did not treat that
substring as wind coverage. The run retained supported solar quotations, exposed
the unmet wind criterion and returned partial status. Perfect citation coverage
of existing claims therefore did not turn an unanswered aspect into completion.

The existing full-text loader excludes all five Wikipedia records because they
are marked excerpt-only. This runner opts into excerpt replay explicitly and
retains search-excerpt scope through the new acquisitions and source records.
It does not relabel those excerpts as fetched full pages.

## Reproduce

Run from the project folder with the same retained artifact directories:

```powershell
uv run --locked python scripts/run_retained_corpora_check.py --include-excerpts --state ".evidenceforge/verification/tavily-full-research-2026-10-05/reports/run_87c056e986b94886974032b599a8fd4c/state.json" --state ".evidenceforge/verification/wikipedia-fallback-2026-10-06/reports/run_eb19102692d94bbfa9e38202e23eabd7/state.json" --output ".evidenceforge/evaluation/retained-corpora"
```

The runner verifies saved byte hashes before replay and rejects inconsistent
access/acquisition scope. Omitting `--include-excerpts` keeps the original
full-text-only admission policy.

## Limits

Both corpora concern energy and were previously inspected. This is a scripted
citation/provenance and missing-aspect check, extending the earlier single-corpus
measurement. It establishes no blind held-out result, general research accuracy,
source truth, independent semantic validation, independent human attestation or
live model quality. Supplied family labels count two groups in the EIA/Utility
Dive set and one in Wikipedia; these signals do not establish independent
corroboration. Saved source text can also include boilerplate.
