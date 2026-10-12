# Provider and report fixes - 12 October 2026

## Result and source changes

Gemini, Tavily and LangSmith were exercised with current credentials. The second
fresh combined campaign completed with all six Gemini roles successful and
relevant NASA search results. This closes current structured-generation execution
verification. It does not establish broad research accuracy.

- Quote-selection contract version 4 uses short evidence/question enum aliases.
  Gemini selections decode to authentic retained IDs and are validated locally;
  passage text is unchanged. Unknown aliases are rejected.
- Version 3's full-ID schema returned HTTP 400. The compact contract passed a
  diagnostic and the new end-to-end campaign. Schema complexity is a suspected
  cause, not a proven provider diagnosis.
- New runs translate generated site operators into Tavily include_domains.
  Historical request profiles retain their original contract and receipt hashes.
- Sentence-boundary extraction avoids local mid-word clipping where boundaries
  exist. Upstream excerpts may still be incomplete. Repeated quotations are
  referenced once. Selected multi-source percentages receive unresolved-value
  qualification without inventing a scientific explanation.
- Existing saved contract versions remain readable. Regression tests cover
  aliases, legacy behavior, domain filtering, exact offsets and presentation.
- CI uses pinned checkout v6 and Ubuntu 24.04. The public browser workflow's
  Python/artifact actions were also updated.

## Measured checks

| Check | Outcome |
|---|---|
| LangSmith | One synthetic allowlisted counter span delivered and read back at 16:27:32 IST; no research payload uploaded |
| First fresh campaign | Five Gemini workflow calls; synthesis HTTP 400; one Tavily HTTP 200 search returned broad homepages; zero claims accepted |
| Compact diagnostic | Used the first campaign's sixth Gemini call; authentic IDs restored; 9,389 tokens; no search |
| Second fresh campaign | Separately approved six Gemini calls and one Tavily search; all six roles succeeded; HTTP 200 search, one credit |
| Second output | Completed/sufficient; three NASA sources, 15 passages, two distinct exact quoted claims; critic approved |
| Second Gemini usage | 27,714 known tokens; dollar cost unknown |
| Offline verification | Nine checks passed; fresh process restored identical terminal state; zero network attempts and no provider calls |

Model: gemini-3.1-flash-lite. Roles: input guardrail, planner, query generator,
coverage evaluator, synthesis and critic. No automatic paid retries occurred.
Both 12 October campaigns exhausted their separate 6/6 Gemini and 1/1 Tavily caps.
Historical failures and receipts remain preserved.

Private evidence remains in ignored directories:
.evidenceforge/verification/gemini-tavily-2026-10-12/ and
.evidenceforge/verification/gemini-tavily-2026-10-12-02/.
Second run: run_808ad22fe80546f8bbc9d534b2397973.
Credentials and private artifacts are excluded from GitHub.

## AI review and remaining boundaries

The report prints each of its two exact NASA PDF quotations once. Local mid-word
clipping and repeated full quote blocks are absent in these selections. However,
the first quotation flattens a multi-planet table, losing reliable column alignment.
The second includes unrelated hydrogen exercise text. Both claims cite the same
PDF despite three sources being retained. The report does not explicitly enumerate
all missing requested percentages.

The model's sufficient status and critic approval are model decisions, not
independent semantic completeness findings. Citation checks establish retained
text correspondence, not table interpretation or source truth. The domain filter
improved this search's relevance without guaranteeing future search quality.

Broader real-source testing, table-aware extraction, semantic coverage checks,
independent human benchmark review and independent OCR accuracy review remain
optional follow-up work. Human sign-off is not claimed. Hosting remains free only
(INR 0/month); the public fixture demo has temporary storage. Durable research is
local. Durable hosted storage and hosted background jobs remain deferred.

## Engineering verification

Source commit: afcad1c30d60f82e264433cf9c2506adce946193.
The 58 focused tests passed locally, along with Ruff lint/format and strict mypy.
[Full Python/container CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38241087132)
passed both jobs, including 482 tests, Ruff, strict mypy, package build, official
Render schema validation, deployment smoke, constrained containers, persistence,
backup/restore and authenticated gateway checks. See [current status](FINAL_STATUS_2026-10-12.md).
