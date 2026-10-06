# Streamlit Community Cloud deployment

The owner requested a public Streamlit demonstration. The entrypoint is
`scripts/streamlit_cloud/streamlit_app.py`, in private repository
`cakhiltej9001-source/evidenceforge-ai`, branch `codex/pending-verification`.
Select Python **3.12** in Advanced settings. This demonstration needs no API keys.

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
The private connection is now available. The source repository has not been made
public, and the Streamlit endpoint is awaiting its first deployment.

After connection, deploy the entrypoint above and set the app's sharing to public.
Verify an actual hosted plan/approval/report flow and downloads before declaring
the public link complete. Do not upload the local `.env` or `.evidenceforge` data.

Official references: [deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy),
[dependency selection](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies),
[private GitHub permissions](https://docs.streamlit.io/deploy/streamlit-community-cloud/status),
and [app sharing](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).
