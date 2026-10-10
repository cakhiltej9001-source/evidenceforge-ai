# Two-topic live-source probe  14 10 October 2026

**Reviewer:** Codex AI. **Human review:** none. **Result:** the completed NASA report needs revision; the subsequent source correction passes offline replay and regression checks. This is a small diagnostic, not an accuracy benchmark.

## Scope and method

The rubric was saved before outcomes in the ignored local verification directory. It checked identity, snapshot integrity, exact quotations, requested scope, qualifiers, budget, and truthful limits. The initially frozen Python, NASA Earth and NASA Mars pages came from their official sites with HTTP 200. The final runs used paragraph-preserving **section excerpts**, whose revised hashes differ from the rubric's initial normalization hashes. Original HTML hashes and both versions of the normalized text remain saved locally.

| Probe | Calls | Measured outcome | AI judgment |
|---|---:|---|---|
| Python list and tuple comparison | 6 of the first 12-call campaign | All structured roles returned HTTP 200; Gemini shortened quotations; exact audit retained zero claims | **Fail** for this answer; no unsupported claims were released |
| First NASA attempt | 4 of the first campaign | Plan approved after its five-minute deadline; no evidence or claims | Operational timeout; no content judgment |
| Isolated quote/critic check on saved Python evidence | 2 of the first campaign | Two full passages copied and citation-audited; critic demanded paraphrase | Quote integrity passed, critic contract needed revision |
| Fresh NASA Earth/Mars workflow | 6 of a separately approved six-call allowance | Six roles succeeded; two sources, six passages, three claims, exact locators; partial report | **Revise**: one duplicate Mars claim, overcounted percentage coverage, and missing-value disclosure absent from report |

## NASA review against the saved rubric

- **Identity and integrity: pass.** The cited IDs refer to the saved NASA case; all locator slices matched retained passages. Both pages are from one publisher, so they provide no independent corroboration.
- **Quotation: pass.** Three retained claims were complete exact quotations. Two were the same Mars passage. Exact matching verifies the saved text, not the truth of the source.
- **Scope: revise.** The report correctly included near-surface Earth values of 78% nitrogen, 21% oxygen and 1% other gases, and named Mars carbon dioxide, nitrogen and argon. The supplied Mars Atmosphere section stated no gas percentages. Coverage wrongly counted the Mars percentage criterion as supported, and the report did not explicitly disclose their absence. The plan also included an unnecessary source-use criterion that became a gap.
- **Qualification: pass within excerpt scope.** The Earth near-surface condition and Mars thin-atmosphere wording were retained. No Mars percentages or temperature-as-composition values were invented.
- **Budget and limits: pass.** All six requests in the second allowance returned HTTP 200, terminal reconnect made no new request, historical benchmark ledgers were unchanged, and dollar cost is unknown. No Tavily search, full-page coverage claim, or human sign-off is implied.

Current code uses a registered quote-aware critic, deduplicates repeated selections, and declines numeric-percentage coverage without a linked numeric percentage. [Full CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38018900500) passed **474 tests**, typing, lint, package, and Docker checks. An **offline replay** of the six saved decisions produced two distinct cited claims and explicitly disclosed absent Mars percentages; its critic approval was scripted and it made zero API calls. The original live result remains preserved. A fresh live report after the last two corrections has not been run.

Local private artifacts: `.evidenceforge/verification/gemini-structured-2026-10-09/` contains the rubric, source manifests, durable receipts, reports, and replay. Credentials remain in ignored local configuration.
