# Phase 10: specialized source and deployment preparation

> Current policy, 8 October 2026: hosting is free only (INR 0/month), superseding the earlier INR 5 allowance. The public Streamlit fixture demo is deployed. See [current status](FINAL_STATUS_2026-10-08.md); dated results below remain historical.

## Current completion — 6 October 2026

The [final phase status](FINAL_STATUS_2026-10-06.md) is authoritative. The
user selected local durable storage under a ₹5/month hosting cap; public hosting
is deferred. The 40-row corrected Gemini comparison and delegated AI review are
complete (136/140 calls, all HTTP 200). Historical ledgers remain 26/30 and 28/40.
Both private CI jobs passed 373 tests and authenticated Docker checks on runtime
source `0f070d134491e2b2a161ecdfdaf987daec2ac904`.

Today's local checkpoint/export and separate-process reconnect passed. Live Tavily
verification is complete; a real Wikipedia fallback also completed after a simulated
primary failure. Gateway health remains public; all other routes are protected when
configured. Streamlit uses loopback behind Caddy. Both gateway and in-app credentials
are required by the future Render template. No public deployment was created.

The following sections preserve earlier implementation and verification history;
their old missing-input/pending notes are superseded by the final status.

## Delivered source extension

NESO's public Carbon Intensity API matches the energy demonstration: solar and
wind percentages in Great Britain's half-hour generation mix, including imports.
The adapter allowlists only `GET https://api.carbonintensity.org.uk/generation`.
It takes no key and does not send prompts, documents or configured model credentials.
Query text never becomes a host, path or request parameter. Redirects and retries
are disabled. Timeout, decoded response size and projected source size are bounded.

Provider schema checks require timezone-aware half-hour timestamps, all nine
unique known fuels, finite nonnegative percentages and a total within rounding
tolerance. Both the documented single-item list and live object envelopes are
accepted. Unexpected fields and malformed/error responses are rejected.

The standard retrieval service records provider identity, retrieval time, query,
call reservation/receipt, source family, hash and retained snapshots. Passages are
explicit deterministic projections of the validated JSON values; quotes verify
these stored projections rather than claiming the API supplied natural-language
sentences. The validated JSON is retained with the source content. Publisher
attribution is NESO; no automatic source quality bonus is added.

From the project folder:

```powershell
cd "C:\Users\AKHILTEJ\Documents\ChatGPT\AI Research agent"
uv sync --locked --extra ui
uv run --locked evidenceforge-energy
uv run --locked evidenceforge-energy --live
```

Default mode is a labeled synthetic fixture. `--live` performs at most one
public GET with fixture planning, retains state under `.evidenceforge/energy`,
and returns failure on retrieval errors or empty evidence. This does not use
Gemini, generate a report, or enable arbitrary live search in the research UI.
The existing full research service still limits its retrieval to offline/local
adapters. This API enriches inspectable evidence through its dedicated command
and the existing RetrievalService interface.

These values are percentages for the returned historical period; check the
returned timestamps. They do not establish absolute MWh, yearly output or a
global solar/wind comparison. Live access and synthetic tests are separate.

Provider contract and attribution:
[official API documentation](https://carbon-intensity.github.io/api-definitions/),
[API terms](https://github.com/carbon-intensity/terms).
The API documentation identifies its data license as CC BY 4.0. Retain NESO
attribution and the period when sharing derived records.

## Deployment files and environment

- `Dockerfile`: Python 3.12.13, uv 0.11.13, locked UI dependencies, no development
  tools in the final image, installed noneditable package, UID/GID 10001.
- `.dockerignore`: build context allowlist excludes dotenv files, keys, documents,
  SQLite databases, traces, generated evaluation records and Git metadata.
- `compose.yaml`: localhost-only port, named `/data` volume, dropped capabilities,
  no privilege escalation. Defaults to fixture reasoning.
- `render.yaml`: free-only web service configuration without a persistent disk;
  automatic deploys disabled. Caddy protects browser routes with a Render
  bcrypt secret while leaving the health path available to the platform.
- `.github/workflows/ci.yml`: locked install, checks/tests/package build, offline
  resume/export smoke, Docker build, cross-container persistence and health smoke.
  [Remote CI passed](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37169054208) on source commit
  `ab66cb464d4b3d024f394ccb3cdc3e5e67746ff8`; subsequent pushes repeat the checks.

| Variable | Default / purpose |
|---|---|
| EVIDENCEFORGE_MODEL_PROVIDER | fixture; select Gemini only for authorized paid use |
| EVIDENCEFORGE_MODEL_ID | Gemini model ID when paid mode is configured |
| EVIDENCEFORGE_MODEL_API_KEY | Private runtime secret, never Docker build input |
| EVIDENCEFORGE_TAVILY_API_KEY | Only explicit Tavily acquisition; unrelated to NESO |
| EVIDENCEFORGE_DATA_DIR | /data in Docker; /data/evidenceforge in Render |
| EVIDENCEFORGE_TRACING_ENABLED | false; external tracing needs separate setup |
| PORT | 8501; hosting launcher reads process environment |
| EVIDENCEFORGE_BUDGET__* | Existing validated call/search/pass/time/token limits |

The container does not copy the project's `.env`. Defaults are offline and no
keys are injected by Compose/Render. Supply secrets through a runtime secret
manager only when paid mode is authorized. Owner names remain local storage
boundaries; all private-service users must be trusted until real authentication
and authorization are added. CORS/XSRF protections are retained.

```powershell
docker compose config --quiet
docker compose up --build -d
# Open http://127.0.0.1:8501
docker compose exec evidenceforge evidenceforge-energy
docker compose restart
# Reconnect to a saved thread in the UI after restart.
docker compose down
```

`docker compose down` retains the named data volume. Avoid `down --volumes`
when saved documents/checkpoints/receipts are needed. Use a mounted directory
writable by UID 10001; custom host/Render mounts must be checked for ownership
before use. Monitor the disk and retain encrypted backups of the complete data
root. Stop the service before filesystem backups so SQLite journals and database
files remain consistent; verify restore to a separate location before relying on it.

Local runtime smoke without Docker:

```powershell
uv run --locked python scripts/deployment_smoke.py --data-dir .evidenceforge/verification/phase10-smoke
uv run --locked --extra ui evidenceforge-ui --port 8502
```

## Hosting limits checked 4 October 2026

Render is a proposed target, not a chosen/created user account or deployed host.
Official platform checks informed the private single-instance template:

- [Private services](https://render.com/docs/private-services) accept internal
  Render network traffic and have no public `onrender.com` address. An authenticated
  gateway or secure access path is needed for remote browser use.
- [Persistent disks](https://render.com/docs/disks) preserve only their mount path,
  attach to one running instance and are unavailable to build/pre-deploy jobs.
  They prevent horizontal scaling and zero-downtime deploys. The free web tier
  cannot provide this required persistent disk.
- [WebSockets](https://render.com/docs/websocket) have no fixed connection timeout
  but close when an instance is replaced. The UI reconnects through stored
  checkpoints; an interrupted provider call remains uncertain and is not retried
  automatically. Connection longevity does not make an in-process job durable.
- [Blueprint schema](https://render.com/docs/blueprint-spec) specifies `pserv`,
  Docker runtime, `autoDeployTrigger: off`, numeric instance count and disk fields.
  The current small compute plan identifier is `0.5c-512mb`; resources must be
  confirmed for the workload before applying it.

UI jobs run in a bounded process executor, not a persistent distributed queue.
Deploy/restart can interrupt active research. Review run state after reconnect;
failed/ambiguous paid receipts still block automatic repeat charges. A production
long-job service needs a queue/worker design and authenticated job ownership.
No numeric HTTP timeout is assumed to establish a long-job guarantee.

## Verification and remaining gates

- Final 44 source and Tavily regression tests passed (11.39 s); earlier runs overlap.
- Repository Ruff checks and format check passed (116 formatted files).
- Strict mypy passed for all 71 source files.
- Locked offline install with UI passed (91 resolved packages).
- Compose, Render and CI YAML parsed successfully; platform validation is separate.
- Live acquisition retained one source and eight located passages, including solar
  and wind, for 3 October 2026 18:30â€“19:00 UTC; no API errors or Gemini calls.
  Run: `run_2b485ed0acce41fcbed9ea005c604c3f` under ignored
  `.evidenceforge/verification/phase10-live/energy/`.
- Offline deployment smoke passed source acquisition, approval, fresh-service
  resume, terminal checkpoint reconnect and report export.
- Wheel/sdist build passed; wheel includes the adapter and energy command entry point.
- Installed `uv run --locked --offline evidenceforge-energy` command passed.
- Temporary workbench launch on 127.0.0.1:8502 returned HTTP 200 after startup.

Docker is absent on this Windows host. A compatible GitHub runner has now passed
image/runtime, constrained research, reconnect, fresh-volume backup/restore and
UI health checks. Render account validation, actual platform disk ownership,
capacity/load and authenticated remote access remain deployment gates. Synthetic
container restore does not establish production disk backup reliability. No Render
resources or public endpoint have been created. The original PDF has now been
reconciled; live-source integration and research-quality validation remain open.




Historical local verification completed: 4 October 2026, 00:43 IST.
Docker execution later passed remotely; the persistent host gate remains open.


## Pending-item repair â€” 4 October 2026

Completed in this audit:

- Validated `render.yaml` against Render's official published JSON schema.
  Result: valid, zero schema errors. Schema SHA-256:
  `a0d4e8a3eb119a1b63657741757e3c25c091b3ce463c4be8c90e8026678d8163`.
  This is local configuration validation, not a deployed runtime check.
- Added `scripts/validate_render.py` and the same validation step to CI.
  Validation reads retained files; it does not fetch schema references or create resources.
- Extended the deployment smoke to persist a thread record and support
  `--reconnect` in another process. Research, export and separate-process reconnect passed.
- Archived the completed synthetic smoke data, restored it to a separate directory
  and verified the restored checkpoint/report in a new process. Backup/restore passed.
  The running user's app data was untouched. No provider calls were made.
- Strengthened CI to run the research workflow in one container and reconnect from
  a fresh container sharing its persistent volume, followed by the UI health smoke.
- Script Ruff/format checks and updated workflow YAML parsing passed.

Reproduce the configuration and restart checks:

```powershell
Invoke-WebRequest https://render.com/schema/render.yaml.json -OutFile .evidenceforge/verification/phase10-deployment/render.schema.json
uv run --locked --extra ui python scripts/validate_render.py --schema .evidenceforge/verification/phase10-deployment/render.schema.json
uv run --locked python scripts/deployment_smoke.py --data-dir .evidenceforge/verification/phase10-restart-smoke
uv run --locked python scripts/deployment_smoke.py --data-dir .evidenceforge/verification/phase10-restart-smoke --reconnect
```

Evidence is retained under ignored `.evidenceforge/verification/phase10-deployment/`
(`render-validation.json`, official schema, `backup-restore.json`, synthetic ZIP).
The restart run is `run_d06ffdba531d46f89223027b92dac106`.

### Latest execution and remaining dependencies

The user authorized private GitHub execution and additional Gemini calls by asking
Codex to act on their behalf. The private [repository](https://github.com/cakhiltej9001-source/evidenceforge-ai) was created and
[CI passed](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37169054208) on commit `ab66cb464d4b3d024f394ccb3cdc3e5e67746ff8`.
Both Python and container jobs succeeded. The container job built the image,
asserted UID 10001, ran research/approval/reconnect/export under 512 MB and
half-CPU limits, restored synthetic data into a fresh volume, reconnected again
and passed UI health. These checks made no model calls. New pushes repeat CI.

| Item | Current evidence | Remaining step |
|---|---|---|
| Docker execution | Passed on hosted GitHub runner; local prerequisites remain unmet | Gate closed for the measured synthetic workload |
| Persistent deployment | Private source repository exists; no Render account/target is configured | User supplies account access, service target and spending cap; check actual platform storage/restart/health/access there |
| Phase 9 execution | 20/20 one-shots available; 28/40 new calls; fresh repaired workflow partial/pass-limit without provider failure | Interpret the disclosed outcomes with richer or narrower versioned cases before research-quality sign-off |
| Phase 9 review | All 20 cases reviewed by Codex as AI, with reasons | Independent human validation remains unclaimed; see AI_REVIEW.md |
| Live Tavily | No key configured here; no call made | Configure EVIDENCEFORGE_TAVILY_API_KEY here or explicitly authorize a named credential source |
| Original reference | Supplied 23-page PDF read and mapped; no rubric/deadline/MCP-server mandate stated | Source-document gate closed; implement the recorded baseline differences before claiming full compliance |

The [extension report](evaluation/EXTENSION_REPORT.md) preserves all original
failures and source versions. The original Gemini ledger remains 26/30.
Automatic approval review rejected searching unrelated project environments for a
Tavily key; no such credential search executed. Hosting access and budget questions
remain pending. No local OS changes or hosted Render resources were made.

Original reference update: see [the PDF reconciliation](submission/ORIGINAL_PDF_RECONCILIATION.md).
The tutorial describes web/documents/API-or-MCP in the same research pipeline;
separate NESO/Tavily acquisition is useful but does not close that integration gap.

## Original assignment runtime fixes — 5 October 2026

The 23-page PDF is mapped and its identified runtime gaps have been addressed with
explicit mixed-source research controls, supported summary paragraphs, per-source
chunk lists and conservative literal working-set deduplication. Prior source records
and citation audits remain authoritative. See the
[implementation record](ASSIGNMENT_FIXES_2026-10-05.md) and updated
[requirements](submission/REQUIREMENTS.md) for tested scope and remaining inputs.
Actual live Tavily and persistent hosting are still unverified; P02–P05 production
guidance and broader research-quality validation remain qualified. Earlier counts
and baseline-gap statements are historical, not additional passing measurements.

## Completed verification — 5 October 2026

[CI run 37253453020](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37253453020)
passed both jobs on source `36d1e44a414bbc9ced7a74fa151b30faffd53593`.
Completed **07:28:22 IST** (01:58:22 UTC):

- **362 tests passed**, 17.90 seconds, Linux/Python 3.12.
- Ruff lint passed; 137 Python files formatted; strict mypy passed, 72 source files.
- Wheel/sdist built; official Render schema and offline deployment smoke passed.
- Docker build, UID 10001, 512 MB/half-CPU research and fresh-container reconnect,
  fresh-volume synthetic backup/restore, and UI health all passed.
- Private repository visibility reconfirmed; 157 allowlisted source files passed
  configured-credential/private-runtime-path checks; 59 local documentation links
  passed. Local paid ledgers and Gemini adapter provenance remained unchanged.

At **07:29:33 IST**, refreshed four provider-free local replay runs. Coverage-loop
completed in two passes; numeric dispute remained partial/no-progress; injected
unsupported draft was repaired once and completed; pass-limited result remained
partial with its gap. Source chunks/paragraph summaries were inspected in the new
saved report. Artifacts remain in ignored `.evidenceforge/demo/phase11/`.

The original PDF/page mapping and the identified baseline engineering mechanics
are addressed within the conservative limits above. Actual Tavily access, persistent
hosting, independent research-quality validation and P02–P05 production guidance
remain open. No new real model/search/API request ran for these fixes.


## Tavily gate closed — 5 October 2026, 08:04 IST

The [live verification record](TAVILY_VERIFICATION_2026-10-05.md) supersedes earlier
missing-credential/unverified-Tavily notes. One full pipeline search returned five
sources and 34 retained passages; all 34 quotation checks passed. Fresh-service
checkpoint recovery and terminal reopening reused saved results. One Tavily credit,
zero Gemini calls. Reasoning was deterministic; boilerplate in the report means
semantic research quality remains open. Hosting, independent review and remaining
production guidance are still pending.


## Hosting access update — 5 October 2026

[Render API access](RENDER_ACCESS_VERIFICATION_2026-10-05.md) is verified (HTTP 200).
Together with the completed Tavily check, this supersedes earlier credentials and
hosting-access pending notes. Actual deployment remains pending: repository
connection, user hosting budget/access choice and persistent runtime checks.
Independent benchmark review and remaining production improvements remain open.
