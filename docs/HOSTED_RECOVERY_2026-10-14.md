# Recovering from a failed Gemini stage

The reported `what is rose ?` run stopped after its first model call, before any
Tavily search or evidence extraction. A separately approved hosted reproduction
on the rebooted recovery build identified a **Gemini request timeout during
question review**: one Gemini call, zero searches and no evidence. Its actual
token consumption was unknown; 5,317 tokens remained reserved. The original
printout alone did not establish an HTTP status or root cause.

## Changes

- Failed runs now show the stage and a fixed, safe explanation. Saved Gemini
  receipts supply an HTTP status when available, including credentials rejection,
  rate/quota limits and temporary server failures. Raw provider messages and
  credentials are never displayed.
- Timeouts and incomplete structured responses have separate receipt statuses.
  Unconfirmed calls remain blocked from automatic replay.
- New workbench runs use policy version 2: semantic question review and planning
  share one structured response. Rejected requests must have an empty plan;
  accepted plans still pass cardinality, distinctness and scope validation.
  The normal one-pass workflow uses five model calls rather than six. New Gemini
  requests have a 45-second transport timeout within 60-second node limits.
  Flash-Lite's combined review uses `minimal` thinking, supported for lower
  latency by [Google's Gemini 3 guide](https://ai.google.dev/gemini-api/docs/gemini-3).
  This does not guarantee provider availability or latency.
- Old saved runs resume using their registered policy and request hashes.
  An explicitly requested fresh attempt for a legacy live-source/document run
  upgrades to the current policy while preserving its question, model, sources
  and per-run budget. Earlier failed receipts are retained.
- **Try again with a new Gemini plan** starts an explicitly requested new run with
  the same question, model, sources and per-run budget. The earlier failed run and
  its usage remain intact. Plan approval is still required.
- **Get source quotations without Gemini** creates a new plan using the same
  selected live sources or documents, with deterministic lexical assessment and
  exact quotations. It uses no Gemini calls; live searches still consume their
  configured search allowance. This is a source-inspection alternative, not a
  claim that Gemini recovered or that semantic research quality was verified.
- JSON downloads now include fixed workflow error records; hosted downloads also
  include safely projected Gemini failure details. Timeline labels identify the
  failed stage rather than just saying a workflow step is unavailable.

These changes apply to the local workbench and the hosted Streamlit entrypoint.
No password or paid hosting resource was introduced. Per-run provider caps were
not increased and no automatic paid retry was added.

## How to get a response

1. Refresh the hosted app after deployment.
2. If the failed run is still selected, inspect its error above the timeline.
3. For a temporary Gemini failure, wait and choose **Try again with a new Gemini
   plan**. For a rate/quota or credentials error, follow the displayed guidance.
4. To get source passages while Gemini is unavailable, choose **Get source
   quotations without Gemini**. Review the plan and click **Approve plan**.
5. If a reboot cleared the temporary run, enter the question again, choose
   **Offline**, keep **Search live web with Tavily** checked, create the plan and
   approve it. With these selections the app searches real sources; it is not the
   synthetic fixture demo. Results depend on the evidence returned.

## Verification

Six new offline regressions passed, with socket/network access blocked. They cover
safe diagnostic projection, HTTP 503 and timeout handling, foreign-scope rejection,
immutable old usage, a fresh Gemini retry, and the source-only alternative. The
real Streamlit UI was exercised from a simulated first-call HTTP 503 to an approved
rose report through both recovery paths. All provider content in these tests was
synthetic, so this is not a fresh live Gemini/Tavily success claim.

Lint, formatting and strict type checking passed (88 source files).
[Source CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38589918480)
passed **533 tests in 32.85 seconds**, plus the container persistence, backup/restore,
UI health and authenticated gateway checks, for source commit `1b1279d`.

The owner reported rebooting and the initial recovery UI was observed on the
hosted app. That live reproduction timed out. The subsequent combined-planning
source fix is pushed; its hosted preflight did not yet observe the new build.
The browser management helper continues to time out.

The [completed live verification and screenshots](ROSE_RECOVERY_2026-10-14.md)
used three Gemini calls and one Tavily search within the approved six-call/one-search
allowance. The combined review passed locally, query generation returned HTTP 503,
and source-only recovery completed with 33 exact-quotation audits. Full Gemini
workflow success remains unverified. No additional calls are being made.
The latest [source CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38606699743)
passed 540 tests for commit `86ab08b`; earlier campaigns remain unchanged.
