# Phase 7: reliability controls and safe observability

Implemented 2 October 2026. This phase verifies the offline fixture workflow. Gemini reasoning
was added separately afterward; see README.md for its configuration and restrictions.
The separate Tavily retrieval adapter has an explicit smoke path; live web research remains
unverified. Ordinary tests use synthetic credentials/adapters and blocked networking.
Gemini paid pause/resume remains disabled pending durable model-call reconciliation.

## Run from PowerShell

```powershell
cd "C:\Users\AKHILTEJ\Documents\ChatGPT\AI Research agent"
uv sync --locked --offline
uv run --locked evidenceforge-research "Compare solar and wind electricity output." --offline
```

The completed run now writes `usage.json`, `progress.json` and `trace_coverage.json` beside the
existing report, state, graph, audit and inspection files. The CLI prints absolute paths.
`progress.json` contains only status, stop reason and counts. The full `state.json` is a private local
artifact and still contains the question and retained source content; do not publish it as telemetry.

For a paused run, use the printed thread ID and the same owner/data directory:

```powershell
uv run --locked evidenceforge-research --cancel THREAD_ID --owner local
uv run --locked evidenceforge-research --resume THREAD_ID --owner local --offline
```

`--cancel` records an owner-scoped durable request; an active workflow checks it during adapter
waits and after graph steps. A paused workflow becomes terminal on resume. Cancellation stops new
calls, cancels the in-flight adapter task, marks an uncertain pending receipt ambiguous and keeps
its search reservation in state. Repeating resume of a terminal run redelivers its saved report.
This local owner label is a scope check, not user authentication.

## Budgets and retry policy

- Planning and query-generation model attempts now count with coverage, synthesis and critique
  under `max_model_calls`. Before an exploratory planning/query call, the graph retains the
  configured quality allowance. Model attempts are counted even when parsing or provider calls fail.
- Search calls reserve in SQLite with `BEGIN IMMEDIATE` before concurrent adapters run. Each retry
  is a new receipt and a new search reservation. A repeated/resumed call reuses its receipt; an
  uncertain pending call is not silently replayed.
- Retries require an adapter to explicitly declare safe categories. The Tavily adapter declares
  only HTTP 429 rate limits retryable. Its bounded `Retry-After` hint is honored when it fits the
  remaining run deadline; hints over 60 seconds stop retry. Authentication, schema, budget and
  internal uncertainty are not retried. No cross-provider fallback is configured, because there
  is no declared compatible provider/scope pair for this offline workflow.
- Pass, rewrite, search, evidence, elapsed and model attempt limits remain enforced. The current
  fixtures do not expose token counts or model prices. A live search with a dollar ceiling remains
  refused until a verified pricing policy is connected to its reservation. A date-stamped
  `PriceTable` can estimate recorded usage, but is not presented as a current provider price.

`usage.json` reports reservations, planning/quality attempts, known token and search-credit totals,
unknown record counts, an estimate only when every component has a price and usage value, and a
known-cost lower bound. `null` means unknown, not zero. Fixture model attempts have no token/cost
receipts, so end-to-end fixture cost is unknown. This is usage accounting, not a billing statement.

## Input, content and URL boundary

Research requests and structured adapter/model outputs use bounded Pydantic schemas. URL results
require HTTP(S), no embedded credentials, and reject loopback, non-global IP, `.localhost`, `.local`
and `.internal` hosts. Tavily sends search only to a fixed HTTPS endpoint, disables redirects, and
does not fetch URLs supplied in results. These result URL checks are admission checks, not a DNS
resolution or web crawler security policy.

Retrieved content, document text and titles stay data. They cannot add graph nodes or grant tools:
query source types come from configured adapters, document selection is owner/request scoped, and
model outputs are parsed into fixed schemas. Source text may contain adversarial instructions; this
phase does not claim a semantic prompt-injection detector. Reports escape source text, and public
progress/traces never include it. The Gemini adapter preserves the fixed-host, structured-output and no-tool boundary.

## Observability

The service disables ambient LangSmith tracing around raw graph state, checkpoint updates and
adapter execution. An injected `LangSmithTraceSink` can emit only allowlisted `PublicProgress`
fields; it requires an explicit client and project. Custom phases include retrieval, rewrite, tool
failure, budget stop, audit, cancellation and finalization. Emission failures are counted but do not
invalidate the research run. `trace_coverage.json` records local attempts and sink acceptance; it
explicitly reports remote delivery unverified. No remote LangSmith call was run in this phase.
No remote trace coverage or successful live model generation is claimed by these fixture checks.

## Verification and limits

The adverse tests cover rate limits, safe/unsafe retry, separate reservations, cancellation while
paused and during an adapter wait, owner isolation, private result URLs, adversarial retrieved instructions, usage unknowns and trace
redaction. Existing tests cover timeouts, authentication, malformed responses, search races,
no-progress loops, repeated calls and checkpoint resume. See `PROGRESS.md` for the final executed
suite, typing, package and CLI results.

The original assignment PDF is unavailable in this workspace. Phase 7 follows the handoff plan;
assignment reconciliation remains open before final project sign-off. Phase 8 UI/export and approval
work is outside this phase.


## Audit follow-up

The Phase 0-7 audit added an explicit service-boundary input review: malformed requests are
rejected and known vague prompts/greetings or punctuation-only prompts request clarification.
Accepted input is unchanged. This policy makes no semantic safety or factual-answerability claim.
A model-derived coverage rationale is now labeled as a structured assessment rather than a fixture.
Test defaults override private local dotenv provider/model/key values; intentional tests can
override those defaults with synthetic settings. See PHASE0_7_VERIFICATION.md for the audit evidence.
