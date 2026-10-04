# Phase 10: specialized source and deployment preparation

Status: local source/runtime implementation verified; deployment configuration prepared.
No hosted deployment has been created.
The user authorized moving to Phase 10 on 4 October 2026. Phase 9 remains open
for independent annotation review and a successful matched Gemini comparison.
The original paid ledger remains 26/30; this phase makes no Gemini calls.

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
- `render.yaml`: reviewable paid private service configuration with a 1 GB disk;
  automatic deploys disabled. No public browser URL or authentication gateway.
- `.github/workflows/ci.yml`: locked install, checks/tests/package build, offline
  resume/export smoke, Docker build, cross-container persistence and health smoke.
  Workflow is prepared locally; no remote CI result is claimed.

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
  and wind, for 3 October 2026 18:30–19:00 UTC; no API errors or Gemini calls.
  Run: `run_2b485ed0acce41fcbed9ea005c604c3f` under ignored
  `.evidenceforge/verification/phase10-live/energy/`.
- Offline deployment smoke passed source acquisition, approval, fresh-service
  resume, terminal checkpoint reconnect and report export.
- Wheel/sdist build passed; wheel includes the adapter and energy command entry point.
- Installed `uv run --locked --offline evidenceforge-energy` command passed.
- Temporary workbench launch on 127.0.0.1:8502 returned HTTP 200 after startup.

Docker is absent on this host: local image build/runtime smoke cannot be claimed.
The prepared CI job supplies container build/persistence/health checks for a
Docker-capable runner, but it has not run remotely yet. Render account validation,
disk ownership, capacity/load, backup/restore and authenticated remote access
remain deployment gates. No resources have been created and no public site is
published. Original assignment/rubric reconciliation and Phase 9 review/provider
comparison also remain open.




Local verification completed: 4 October 2026, 00:43 IST. Docker/host gates remain open.


## Pending-item repair — 4 October 2026

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

### Exact remaining dependencies

| Item | Verified cause | Concrete next step |
|---|---|---|
| Docker execution | Docker absent; this PC reports ~4 GB RAM and firmware virtualization disabled. WSL status exits 50; Windows feature queries require administrator elevation. | Use a compatible hosted Docker runner. A private `cakhiltej9001-source/evidenceforge-ai` repository and CI run have been proposed and need approval. |
| Hosted deployment | No Git remote or Render credentials configured; no matching research repository found. GitHub login works outside the sandbox. | Confirm the hosting account/target and repository; deploy the reviewed private service configuration, then check storage ownership, health, restart and runtime capacity there. |
| Phase 9 provider comparison | Original ledger remains 26/30; the prepared extension needs at most 32 new attempts. | Approve the separately requested cap of up to 40 additional Gemini calls before execution. |
| Phase 9 annotation sign-off | All 20 labels remain draft; no completed independent review record supplied. | A person reviews ANNOTATION_PACKET.md and supplies decisions plus reviewer name/date. |

The hardware requirements are from [Docker's Windows installation documentation](https://docs.docker.com/desktop/setup/install/windows-install/).
Canonical Render schema source: [official Blueprint validation guidance](https://render.com/tutorials/advanced-blueprint-patterns/introduction).
No Docker installation, OS feature change, restart, repository upload, hosted resources
or additional Gemini calls have been performed during this audit. Docker and hosted
runtime checks are not claimed as passed. Local synthetic backup/restore does not
establish backup reliability for a future hosted production disk.
