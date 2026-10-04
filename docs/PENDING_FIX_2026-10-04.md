# Pending work repair — 4 October 2026

## Completed local changes

- Docker CI now runs the research/checkpoint/UI checks under 512 MB and half-CPU limits matching the proposed service size.
- Added an effective UID 10001 assertion and a synthetic volume backup/restore into a new volume, followed by checkpoint/export reconnect.
- Workflow YAML parsed successfully; the pinned setup-uv action commit was verified to exist through a read-only GitHub request. These changes are prepared and have not executed in Docker.
- Added `scripts/prepare_annotation_review.py` and local review instructions. The form shows all 20 frozen cases and their corpus/reference labels, requires a real reviewer name/date/attestation, leaves decisions unset, requires revision notes, and downloads a decision record without changing dataset status.
- Review form HTTP 200 verified: 20 unique cases, 20 required decisions, zero preselected approvals. JavaScript syntax and repository Ruff lint/format checks passed (127 files formatted).
- Source preflight checked 145 files before the new form/docs; no configured credential values or private runtime paths were found. Refresh the retained manifest before any upload.
- Downloads archives `AI Agents.zip` and `assignment_part_2.zip` were inspected by filename; neither contained the expected assignment PDF. They were not extracted or treated as repository instructions.

Review form: `http://127.0.0.1:8504/`; generated local artifact `.evidenceforge/review/phase9/index.html`.

## External execution and missing inputs

An attempt to execute the prepared Phase 9 extension under the proposed 40-call allowance was rejected by automatic approval review before execution. The stated reason was that only the original 30-call cap is explicitly authorized, while the new calls send benchmark payloads to Google and may incur cost. No workaround or retry was made. The base ledger remains 26/30; no extension provider call occurred.

Explicit requests for the separate 40-call allowance and private `cakhiltej9001-source/evidenceforge-ai` repository/upload/CI are pending. Source excludes credentials and local research data. No repository was created or uploaded. No hosted service was provisioned.

Independent human annotation sign-off still requires a person to complete the review. The original assignment PDF/rubric, a hosting account/target and Tavily credential are still unavailable. The local reviewer form and prepared CI make the next steps concrete; they do not close those validation gates.

## Later execution supersedes the pending approvals above

The user subsequently authorized Codex to act on their behalf. Automatic approval
review accepted the additional 40-call Gemini allowance and private GitHub execution.
The extension and repairs used 28/40 calls; all 20 one-shot cases now have usable
responses. Private repository upload and Docker CI passed. All 20 annotations
received a recorded AI review. See evaluation/EXTENSION_REPORT.md and PHASE10.md.
Original PDF/rubric, persistent hosting and Tavily configuration remain missing;
human validation is unclaimed. The earlier Gemini rejection is historical.
