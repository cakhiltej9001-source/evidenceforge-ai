# Phase 9 annotation review

The benchmark dataset `diverse_dataset.json` is a Codex draft with status
`draft_requires_human_review`. It is not a human-validated gold set.

An independent reviewer should inspect all 20 cases and record a decision for each:

1. Confirm the question is answerable from its frozen synthetic corpus.
2. Confirm every required answer aspect in `reference_passages`.
3. Confirm the dispute labels for cases `diverse_17` and `diverse_18`.
4. Confirm the abstention labels for cases `diverse_19` and `diverse_20`.
5. Record the reviewer, review date, dataset SHA-256, and reasons for changed labels.

Preserve the original draft. Put approved labels in a new versioned dataset and rerun
all variants with its own frozen manifest. The loader accepts `human_reviewed` only with `reviewed_by` and `reviewed_at` metadata.
Validation checks their presence; it cannot establish that review truly occurred.



Use `ANNOTATION_PACKET.md` to record a decision for each of the 20 cases. The
machine-checked draft consistency results are in `ANNOTATION_AUDIT.json`.

## Local reviewer form

A person can inspect the same frozen packet and export decisions using the local form:

```powershell
uv run --locked python scripts/prepare_annotation_review.py
uv run --locked python -m http.server 8504 --bind 127.0.0.1 --directory .evidenceforge/review/phase9
```

Open `http://127.0.0.1:8504/`. Every case requires an explicit approve/revise choice;
revisions require notes. Name, review date and a human-review attestation are required.
No approvals are preselected. The form downloads `annotation-review-decisions.json`
and does not change the dataset or claim review has occurred merely by generating
or opening the page. Retain this record and apply approved revisions to a new
versioned dataset before rerunning benchmark variants. This form has no external
requests or provider calls. Do not serve the project root.

## Delegated review record

On 4 October 2026 the user asked Codex to act on their behalf. Codex recorded a
decision and reason for every case in [AI_REVIEW.md](AI_REVIEW.md) and
[AI_REVIEW.json](AI_REVIEW.json). This is AI review; the frozen dataset status and
hash are unchanged. The first 16 questions need tighter scope or richer corpora
for real quality evaluation. No human name, attestation or approval was fabricated.
