# Retained public-source replay - 7 October 2026

Report prepared on **8 October 2026** from the
[retained measurement JSON](RETAINED_PUBLIC_REPLAY_2026-10-07.json).
The runner reuses integrity-checked snapshots and scripted reasoning; it makes
no new search or model-provider calls.

## Corpus and measured outcomes

Five retained public sources comprise **four EIA pages and one Utility Dive page**.
This source count does not establish independent corroboration.
Input state SHA-256:
`fbb850ae05d02398433f87c2228f82414f99d2dfa73be199b65dc46ed955d2ae`.

| Case | Input results | Sources | Claims | Evidence / exact locators | Outcome | Gaps |
|---|---:|---:|---:|---:|---|---:|
| Available snapshots | 5 | 5 | 30 | 30 / 30 | completed / sufficient | 0 |
| Duplicate snapshot | 6 | 5 | 30 | 30 / 30 | completed / sufficient | 0 |
| Missing aspect | 5 | 5 | 20 | 20 / 20 | partial / pass_limit | 1 |
| Empty corpus | 0 | 0 | 0 | 0 / 0 | insufficient_evidence / no_evidence | 2 |

Citation precision against retained text and citation coverage were **1.0** in
each case with claims; both were N/A in the empty case. Citation coverage counts
existing claims with citations; the missing-aspect outcome still discloses an
unanswered criterion. No quantitative conflicts were reported in this corpus.

Measured case latencies were 37.2074, 29.9752, 43.1968 and 34.8539 seconds respectively.
They include local execution overhead and are not live-model latency comparisons.

All five checks were true:

- Available snapshots produced supported citations.
- Duplicate input did not increase sources, evidence or claims.
- The missing aspect did not produce a completed outcome.
- Empty input produced no claims.
- Every retained passage matched its exact locator.

## Reproduction and limits

```powershell
uv run --locked python -m evidenceforge.evaluation_retained --state ".evidenceforge/reports/RUN_ID/state.json" --output ".evidenceforge/evaluation/retained-public"
```

Use the original saved state with its matching artifact folder; replace
`RUN_ID` with the retained run. The loader excludes scoped documents and fixture
sources and verifies retained hashes before replay.

These are citation/provenance mechanics for one energy corpus using scripted
reasoning. Source truth, independent semantic validation and independent human
review remain **false** in the measurement. This run supports no general claim
about research accuracy or live LLM quality. **Provider calls: 0** in every case.
