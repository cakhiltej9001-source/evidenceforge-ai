# Phase 9 Gemini extension plan

Prepared 4 October 2026, Asia/Calcutta. Status: dry run verified; execution approval pending.

The original benchmark ledger is fixed at 26 of 30 paid reservations. Its result
files remain the base for this extension. A separate proposed allowance of up to
40 additional calls has been requested but has not been approved.

The extension would run the eight missing one-shot cases (`diverse_01` through
`diverse_08`) and two full-agent cases (`diverse_01`, development, and `diverse_13`,
held out). Each full run uses the fixture full-variant budgets: three passes,
zero rewrites, 12 model calls, and eight searches. The maximum planned attempts
are 8 + 2 × 12 = 32. The proposed cap includes eight spare reservations, but the
runner does not retry a failed request automatically.

Inspect the plan from the project root:

```powershell
uv run --locked python -m evidenceforge.evaluation_extension --additional-call-cap 40
```

The default command performs no Gemini request and makes no paid reservation.
Paid work requires the explicit `--execute` option and separate user authorization.
Its ledger and results use `.evidenceforge/evaluation/phase9_extension`, separate
from the original run. The manifest freezes the dataset, budgets, model, source
hashes, and base-result hash before provider work. A changed manifest is rejected.

Independent human annotation review is still required using `ANNOTATION_PACKET.md`.
The runner cannot establish that a human reviewed the labels. The provider may
still rate-limit requests; failures and unknown usage will be retained explicitly.
