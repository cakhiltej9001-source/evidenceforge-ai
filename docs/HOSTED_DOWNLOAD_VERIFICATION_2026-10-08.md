# Hosted download verification - 8 October 2026

The public [EvidenceForge fixture demo](https://evidenceforge-ai-akhiltej.streamlit.app/)
passed actual headless Chromium downloads and fresh-visitor checks.
[Browser CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/37751643343)
completed at **14:13:49 IST** on 8 October. The verifier revision was
`e2c02e6f78315e296b3983bd0d8a72e2ec6da35f`; the deployed app's Git revision was not observed.

## Measured result

All eight checks in the [sanitized result](evaluation/HOSTED_DOWNLOAD_2026-10-08.json)
passed. The browser created and approved one fixed synthetic plan, completed its
report, received both download events and saved the downloaded files before
inspecting their bytes.

| Download | Saved bytes | Checks |
|---|---:|---|
| report.md | 1,263 | Expected filename, completed status, fixture disclosure and solar/wind findings |
| report.json | 22,939 | Expected filename, version 1, synthetic_fixture/offline_fixture fields, completed progress and report |

A second independent browser context exposed no saved thread and no report
download controls. The public UI exposed the Offline provider, no document
upload and no live-source controls. Provider calls requested by the check: **0**.
No credentials, cookies, storage state or private research were supplied.

Two earlier runs stopped before plan creation because the verification script
misread Streamlit's provider selector. The checker now inspects its accessible
menu. Production UI code was unchanged by those compatibility fixes.

## Reproduce

From an authenticated checkout of the private repository:

```powershell
gh workflow run public-demo.yml --ref codex/pending-verification
```

The workflow targets only this public synthetic demo. It uploads sanitized JSON
and masked screenshots for seven days. Downloaded raw reports stay in a temporary
directory and are not uploaded or committed.

The checker uses [Playwright download events and save_as](https://playwright.dev/python/docs/downloads).
Its isolated browser installation and Linux runner are defined in
[`public-demo.yml`](../.github/workflows/public-demo.yml).

## Limits

This is one fixture case and a fresh-visitor isolation check. It does not
establish broad factual accuracy, persistent hosted storage, an independent
human review or a security audit. The existing integration tests separately
reject cross-owner checkpoint access. Hosting remains free only (INR 0/month);
durable full-workbench storage stays local.
