# Public demo deployment

The app has a Docker deployment configuration. A localhost URL such as
`http://127.0.0.1:8511/` is accessible only on the computer running the server;
it is not a public share link. A separate public Streamlit fixture demo is now
live at [EvidenceForge](https://evidenceforge-ai-akhiltej.streamlit.app/).
See [verified Community Cloud deployment](STREAMLIT_CLOUD.md). The Render
configurations below are optional alternatives and have not been applied.

## Available configurations

| Configuration | Purpose | Saved research |
| --- | --- | --- |
| Local UI | Current selected deployment | Durable in the local `.evidenceforge` directory |
| Streamlit Community Cloud | Deployed public fixture demonstration | Temporary, scoped to the current browser session |
| [`render.free.yaml`](../render.free.yaml) | Optional login-protected public demonstration using synthetic fixtures | Temporary; lost on restart, redeploy or idle shutdown |
| [`render.yaml`](../render.yaml) | Paid Render deployment with a persistent disk | Durable on the attached disk; requires a separately approved hosting budget |

The owner selected local durable storage under a ₹5/month hosting cap. The free
configuration is prepared for review; applying it requires accepting temporary
storage for a separate public demo. The local installation keeps its saved work.

[Render's free-service documentation](https://render.com/docs/free) states that
free services cannot attach a persistent disk, lose local SQLite/upload files
on restart or shutdown, and shut down after 15 idle minutes. First access after
shutdown can take about a minute. Free service compute does not by itself cap
workspace bandwidth or build overages when a payment method is configured.
Check billing controls before provisioning within the owner's spending limit.

## Deployment steps after accepting the free demo

1. Confirm that workspace billing controls prevent spending above the approved
   cap. Do not select a paid compute plan or attach a paid disk.
2. Grant Render access to the private `evidenceforge-ai` repository through its
   GitHub connection. The repository does not need to become public.
3. Create a Blueprint from the approved repository branch, selecting
   `render.free.yaml` as the Blueprint path. Confirm the preview contains one
   **Free** Docker web service and no disks or databases before applying.
4. Supply two private password hashes for one strong password: Caddy's bcrypt
   hash and the app's PBKDF2 hash. The template requests both values instead of
   storing them in Git. The username is `admin` at both login layers. Refer to
   [setup](submission/SETUP.md) and the authenticated gateway checks in
   [CI](../.github/workflows/ci.yml) for the hash commands. Use a privately
   generated deployment password, not CI's fabricated test password.
5. Deploy the Docker service and wait for a healthy status. It uses fixture
   models with tracing disabled; Gemini and Tavily credentials are not copied
   from the local app.
6. Verify the actual Render HTTPS URL: health returns HTTP 200; anonymous root,
   media, uploads and WebSocket requests require authentication; wrong
   credentials fail; authenticated access opens the app. Complete one synthetic
   research run and download its report. A hosted check remains pending until
   these checks run against the real service.
7. Share the HTTPS URL and provide login credentials privately. Download reports
   before leaving the demo, since hosted files are temporary. Use the local app
   for research that needs durable checkpoints and uploads.

## Restore local access

Run from `C:\Users\AKHILTEJ\Documents\ChatGPT\AI Research agent`:

```powershell
uv run --locked --extra ui evidenceforge-ui --host 127.0.0.1 --port 8511
```

Keep that terminal running, then open `http://127.0.0.1:8511/`. Closing the
server stops browser access. Restarting it preserves the local data directory.
`ERR_CONNECTION_REFUSED` means no reachable server is listening at that address;
it does not establish that the Docker app cannot be deployed.
