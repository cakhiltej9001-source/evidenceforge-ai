# Pending-work repair — 6 October 2026

This record captures the continuation after the user approved browser login
protection and up to 140 additional Gemini calls for a corrected comparison.

## Completed locally

- Added a semantic input classifier before the production Gemini manager. It
  accepts research questions and returns bounded guidance for gibberish,
  non-research, manipulation and vague inputs. Rejected inputs make no search
  calls.
- Added ordered Tavily-to-Wikipedia fallback with per-provider budget receipts,
  typed failures, bounded response sizes and source-provider provenance.
- Added lowest-score evidence eviction at the configured evidence limit while
  retaining immutable snapshots, acquisition records and pinned report claims.
- Added bounded local node traces and optional payload capture. Default traces
  contain metadata only and never export to a remote tracing service.
- Added a Caddy gateway to the Docker image. Render's health path is public for
  health checks; all other routes can require Basic Auth. Streamlit listens only
  on loopback behind Caddy. The gateway's bcrypt hash is a Render secret.
- Added a six-stage semantic-acceptance/replay test. Ruff, formatting and mypy
  pass; the new test passes. The offline v2 comparison completed 40 rows (20
  single-response and 20 workflow) with zero provider calls.

## External gates

- Gemini comparison: **not run**. The user approved 140 calls, but the Codex
  approval service rejected the network execution before the command ran because
  the environment approval-credit limit was exhausted. No new Gemini call or
  charge occurred; the earlier 26/30 and 28/40 ledgers remain separate.
- Hosted deployment: **staged, not created**. Render API access is verified,
  but the monthly spending cap and repository-to-Render connection are still
  absent. No paid Render resource was created.
- Independent human benchmark review: **still pending**. Codex's delegated AI
  review is recorded and is not represented as human sign-off.

## Reproduction

```powershell
.venv\Scripts\python.exe -X utf8 scripts/run_corrected_benchmark.py `
  --mode fixture `
  --output .evidenceforge/evaluation/phase9_v2_fixture `
  --execute
```

The paid command is intentionally documented but not executed in this run:

```powershell
.venv\Scripts\python.exe -X utf8 scripts/run_corrected_benchmark.py `
  --mode gemini `
  --output .evidenceforge/evaluation/phase9_v2_gemini `
  --execute
```

It uses the configured `gemini-3.5-flash-lite` model and enforces a durable
140-call cap. A fresh output directory is required; an interrupted case is
marked for review rather than retried automatically.
