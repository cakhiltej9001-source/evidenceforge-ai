# LangSmith verification - 8 October 2026

The owner supplied the API key for this project. It is saved only in the ignored local `.env`; no key is stored in source or this record.

One span in `evidenceforge-synthetic-verification` used fixed synthetic counters and explicit full sampling. Exact completed-span name, inputs and outputs were checked by receipt readback.

| Check | Result |
|---|---|
| Credential configured | true |
| Remote delivery verified | true |
| Tracked / verified receipts | 1 / 1 |
| Unverified / omitted receipts | 0 / 0 |
| Research payload uploaded | false |
| Gemini / Tavily calls | 0 |

Reproduce intentionally:

```powershell
uv run --locked python -m evidenceforge.trace_verification --execute --output .evidenceforge/verification/langsmith-synthetic.json
```

Without `--execute`, the command reports readiness and sends nothing. Ordinary research tracing stays opt-in. This verifies synthetic counter delivery; it does not verify full research payload tracing or model quality.
