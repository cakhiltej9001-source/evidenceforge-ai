# Login-protected live research on Streamlit - 13 October 2026

The owner approved using the saved Gemini and Tavily keys behind login and
reported saving the prepared secrets in Streamlit App settings.

## Behavior

- The Community Cloud entry point supports live research with private secrets.
  Live mode always forces the existing owner login, even if an environment
  setting tries to turn authentication off. Missing keys or a missing password
  hash stop setup before any research control is shown.
- After sign-in, configured Gemini and Tavily search are selected by default.
  Document uploads and the optional energy source are available.
- Local workbenches also select configured Gemini and Tavily by default.
  Offline reasoning remains selectable. CLI and API use their existing explicit
  live-source flags and configured keys; offline worker queues remain offline.
- Hosted defaults allow at most 6 model calls, 1 search, 1 retrieval pass and no
  automatic retry per research run. Each new run requires Create plan and then
  plan approval. Limits appear before submission.
- Hosting remains free only. Provider requests can consume credits or incur
  provider charges. Hosted storage is temporary; download reports. Durable
  research remains available locally.
- Research and tracing payloads are not automatically exported to LangSmith.
  The explicit public fixture mode remains available for demonstrations.

## Private configuration

Use Streamlit App settings > Secrets. Root keys are:
EVIDENCEFORGE_CLOUD_MODE = live, EVIDENCEFORGE_MODEL_PROVIDER = gemini,
EVIDENCEFORGE_MODEL_ID, EVIDENCEFORGE_MODEL_API_KEY,
EVIDENCEFORGE_TAVILY_API_KEY, EVIDENCEFORGE_AUTH_USERNAME,
EVIDENCEFORGE_AUTH_PASSWORD_HASH and EVIDENCEFORGE_BUDGET.

Values must use valid TOML quoting. The password hash uses the existing PBKDF2
login helper. The owner has an ignored private secrets.toml and login.txt bundle
under .evidenceforge/hosting/streamlit-live-2026-10-13/. Neither file is published.

To intentionally serve the anonymous fixture demonstration instead, set
EVIDENCEFORGE_CLOUD_MODE = demo; live provider keys are cleared for that mode.
The historical public-demo browser workflow is only for this explicit fixture
mode and is not a live-research check.

## Verification

Network-blocked tests verify forced login, retained private key configuration,
bounded default budgets, invalid-mode redaction, actual synthetic login before
live controls appear, configured UI defaults, fixture visitor isolation and
existing local create/edit/approve/download behavior.

The initial combined run had 8 passes and one test-only assertion failure from
using an unsupported AppTest session-state property. That assertion was
corrected; the final 7 new live-mode tests passed, including a synthetic sign-in
and the missing-secrets setup error.
The existing 3 UI/demo tests passed in the initial combined run. Ruff passed and
mypy found no issues in the 2 changed source modules.

No new Gemini or Tavily requests were made while enabling the app. Earlier
bounded live API tests remain separate from hosted deployment verification.
Hosted activation and anonymous login-gate observation are recorded separately
after publishing; broader research accuracy remains unclaimed.

[Streamlit deployment](STREAMLIT_CLOUD.md) |
[Earlier live provider screenshot](LIVE_PROVIDER_SCREENSHOT_2026-10-13.md)

## Source CI result

[CI for source 8940662](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38409945905)
passed both Python and container jobs: 515 tests in 39.30 seconds, strict mypy
for 87 source files, lint/format, package build, deployment smoke, constrained
Docker persistence/backup and authenticated gateway checks.

Initial anonymous browser checks observed the earlier fixture UI. The owner
reported saving secrets and rebooting; hosted activation is being rechecked.
Source verification does not by itself prove the hosted revision has updated.
