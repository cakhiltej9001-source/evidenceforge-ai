# Streamlit Community Cloud deployment

The owner requested a public Streamlit demonstration. The entrypoint is
`scripts/streamlit_cloud/streamlit_app.py`, in private repository
`cakhiltej9001-source/evidenceforge-ai`, branch `codex/pending-verification`.
Select Python **3.12** in Advanced settings. This demonstration needs no API keys.

**Live public URL:** [Open EvidenceForge](https://evidenceforge-ai-akhiltej.streamlit.app/).
Choose **Create plan → Approve plan**. Public sharing is enabled; the source
repository remains private.

A fresh HTTP client without account credentials or browser cookies reached the
public app with HTTP 200 after Community Cloud's normal redirect chain; it did
not finish at a sign-in destination.

## Verified deployment

On 6 October 2026 the hosted app created a plan, accepted its approval and
completed the synthetic second-pass report with two retained findings, two
retrieval passes, two citation checks and no tool errors. Markdown and JSON
download controls were present. The browser tool did not observe a download
completion event; the local integration test verified both export controls.
Visitor separation passed the integration test, including rejection of a second
visitor's attempt to read the first visitor's checkpoint.

[Runtime CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37505393414)
passed for source `6fb5241c1dd36e18a7ae86ba2b61fee41732fe0f`, including Python
checks and Docker verification. The entrypoint's live model and search keys are
blank, fixture reasoning is enforced and tracing is disabled. No live provider
calls were made during this deployment or verification.

![Completed hosted fixture report](images/streamlit-public-demo.jpg)

The adjacent `requirements.txt` is exported from the project's existing lock with
the UI extra and without development packages or an editable project requirement.
Community Cloud checks the entrypoint directory before the repository root. The
entrypoint adds the repository's `src` directory to its import path.

## Public demonstration behavior

- Synthetic fixtures only; no Gemini or Tavily calls and no tracing payloads.
- No document uploads or caller-supplied workspace names.
- A server-generated scope for each browser session. Other visitors cannot list
  or open its saved runs.
- Temporary hosted storage. Download reports before leaving; reconnection is
  limited to the current browser session.
- The full local workbench retains documents, live sources and durable storage.

## Deployment connection

Streamlit is signed in to the GitHub account. The initial deployment form rejected
the private EvidenceForge repository because its private access was not connected.
The GitHub
authorization preview requests the ability to read and write **all public and
private repository data**, broader than just this project. Approval of that new
permission was explicitly approved by the owner, who completed GitHub verification.
The private connection is available. The source repository has not been made
public. The deployed Streamlit app's **Make this app public** setting was enabled
and checked again after saving.

For future redeployment, use the entrypoint above and retain public fixture-only
sharing. Do not upload the local `.env` or `.evidenceforge` data.

Official references: [deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy),
[dependency selection](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies),
[private GitHub permissions](https://docs.streamlit.io/deploy/streamlit-community-cloud/status),
and [app sharing](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).

## Export verification update - 8 October 2026

[Current source CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37717750091) passed all 445 tests and both jobs on `b65fd0259907fd6b1749566cbe0f1e5447f084e0`. Integration checks inspect Markdown/JSON filenames and actual download bytes, fixture disclaimers, completed JSON progress and visitor isolation. Download actions skip a UI rerun. Fresh anonymous HTTP access returned 200 after the update. The browser helper failed with a Windows sandbox setup error, so actual hosted download completion remains unobserved. No live provider call or private payload was sent by the public demo.
