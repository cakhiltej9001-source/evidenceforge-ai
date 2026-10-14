# Hosted configuration repair - 14 October 2026

The hosted screenshot showed Invalid settings: model configuration. That message
comes from live-model validation when the model ID or model API key is absent;
the screenshot alone does not identify which field was missing.

## Repair

- Live Cloud mode now sets Gemini explicitly instead of inheriting a fixture
  provider left by a previous demo rerun.
- An omitted or blank model ID uses gemini-3.1-flash-lite, the model verified in
  earlier bounded live checks. An explicitly configured model is preserved.
- Gemini keys can use EVIDENCEFORGE_MODEL_API_KEY, GEMINI_API_KEY or GOOGLE_API_KEY.
  Tavily keys can use EVIDENCEFORGE_TAVILY_API_KEY or TAVILY_API_KEY. Explicit
  canonical secret entries take precedence over aliases and environment values.
- Cloud readiness is checked before generic Pydantic validation. Missing entries
  are named without exposing their values, with a Streamlit Secrets action.
- Password-free access, visitor scopes, per-run budgets and tracing controls
  remain in force. A missing API key is never replaced by a fixture answer.

A complete private secrets bundle was prepared and validated using the saved
local credentials. The owner reported saving it to Streamlit on 14 October.
It remains ignored under .evidenceforge/hosting/streamlit-live-2026-10-14/;
no key values or login credentials are published.

Offline regression coverage checks default-model restoration, both standard
Gemini key names, Tavily aliases, canonical precedence, stale blank fields,
redacted missing-field errors and the actual hosted setup-error UI. Existing
hosted login/public scopes and general configuration tests are included.
No Gemini or Tavily calls were made for this repair. Static settings validation
is separate from hosted activation and successful provider generation.

## Local verification

The first combined run passed 25 tests and timed out in the first setup-screen
check while importing the research UI. Readiness validation now precedes that
heavy import. All 8 new regression cases then passed in 11.17 seconds. Ruff
lint/format passed and mypy reported no issues in the changed Cloud module.
The owner reported saving the complete validated private secrets bundle.

## Full source CI

[CI for 0adf6e8](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38488334349)
passed both jobs: 525 tests in 34.74 seconds, strict mypy for 87 source files,
lint/format, package build, deployment smoke and container checks. The remote
Dev Container commit was preserved before publishing the repair.

The private Streamlit configuration was saved by the owner. Hosted activation
is checked separately; no fresh provider calls were submitted.

## Follow-up environment repair

The owner still observed the same generic error after the first update. A Linux
environment can contain both uppercase and lowercase names: a stale lowercase
blank can shadow a valid canonical field when Pydantic folds environment keys.
Cloud bootstrap now normalizes those names and removes case collisions before
validation, and accepts lowercase secret names. Regression coverage reproduces
the generic error before normalization and validates the same credentials after.

The setup error screen now displays Configuration loader: 2026-10-14 v2 and
points to Streamlit Secrets. This distinguishes the updated loader from an
older hosted revision; the owner's current hosted view still requires recheck.
