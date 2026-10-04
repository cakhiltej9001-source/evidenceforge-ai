# Four-minute demonstration script

## Prepare before presenting

Run `uv sync --locked --extra ui`, then `uv run --locked python scripts/prepare_demo.py`.
Start `uv run --locked python -m http.server 8503 --bind 127.0.0.1 --directory
.evidenceforge/demo/phase11` and open http://127.0.0.1:8503.
Keep `docs/submission/EVALUATION.md` available. The replay HTML, manifest and
report links come from actual fresh local service runs; they are explicitly
synthetic, not a live Gemini performance demonstration. Preparation time is
outside the 3–5 minute presentation. Stop the server afterward with Ctrl+C.

## Presentation — approximately 4 minutes 30 seconds

| Time | Action | Suggested narration |
|---|---|---|
| 0:00–0:25 | Show the replay label and four scenario links | “EvidenceForge makes it possible to inspect where a report's claims came from. These are synthetic captured workflow runs; they show mechanics, not verified measurements.” |
| 0:25–1:10 | Open Coverage Loop; show two passes, two claims and state/report links | “The first batch supplies solar evidence. Wind remains uncovered, so the workflow generates a follow-up query. A second batch supplies wind and the run completes within its limits.” |
| 1:10–1:45 | Click either claim; show its exact passage, locator and selected support graph | “The claim refers to this retained span and source version. The graph connects the finding to evidence and the question. A citation match establishes retained-text support; it does not prove source truth.” |
| 1:45–2:30 | Open Dispute; show partial/no_progress and contradictions/comparisons | “The synthetic Northfield sources disagree under matching conditions. Both sides stay visible. Copied families and changed dates/units are treated explicitly; this run discloses unresolved work.” |
| 2:30–3:15 | Open Audit Repair, injected first draft, observed drafts and final report | “The harness deliberately supplies a bad first draft. The real citation checker rejects its support and reserves one rewrite. The second draft uses retained quotes; the bad number is absent from the final report.” |
| 3:15–3:50 | Open Partial Result; show one pass, pass_limit, unresolved criterion | “With only one retrieval pass allowed, the supported solar claim remains and the missing wind criterion is disclosed. The system does not invent an answer to complete the report.” |
| 3:50–4:30 | Show the evaluation table and limitations | “All 40 synthetic case variants executed. The loop improved exact aspect coverage on this draft set. Human annotation review and a successful matched Gemini comparison are still open, so no general accuracy claim follows from these numbers.” |

## Optional UI interaction outside the timed replay

Start `uv run --locked --extra ui evidenceforge-ui`. Choose offline reasoning,
enter the solar/wind question, review/edit the plan, approve its current version,
then inspect a finding and download the report. Use the timeline/coverage panels
for a live local workflow. A fresh process can reconnect through the saved thread.
The dedicated repair scenario is in the replay harness, not an unlabeled UI preset.

## Optional live source segment

`uv run --locked evidenceforge-energy --live` performs one public NESO acquisition
with no Gemini calls. Display its actual returned period and percentages; these
are GB half-hour mix shares, not absolute MWh or a global solar/wind comparison.
If access fails, disclose the error or use the saved Phase 10 acquisition as a
**captured historical API run**, showing its timestamp. Do not label it current.
This segment is optional and is not required for the offline demonstration.

## Safe presentation claims

- Show actual manifest/report values; do not describe partial runs as completed.
- Label the first incorrect draft as deliberate test input.
- Fixture URLs are placeholders; inspect the local retained support instead of
  claiming the placeholder website is a live research source.
- Original assignment PDF/rubric compliance, human-reviewed benchmark validity,
  remote CI and hosted runtime are not verified.
- Do not show private keys, real uploaded documents or raw historical paid data.
