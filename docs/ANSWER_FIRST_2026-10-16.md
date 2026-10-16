# Answer first, then key findings

## Requested presentation

The workbench report and its Markdown download show **Answer** before **Key Findings**.
The earlier reference-only Summary could make a simple answer hard to find.

The Answer section selects short, exact text from already cited and supported
quotations. For example, if the retained evidence says "Hyderabad is the capital
of Telangana.", that sentence can appear first with its source citation. Full
quotations, source links, saved passages and downloads remain available below.

## Evidence boundaries

- Answer excerpts are contiguous spans of an audited quotation. They do not add
  facts, paraphrase the source, rewrite canonical claims or make model/search calls.
- Lexical ranking favors relevant, concise sentences and excludes common social
  metadata, question-only text, markup and incomplete pronoun-led fragments.
- Scope qualifiers stay with their whole short quotation; otherwise that excerpt
  is omitted. Relevant unresolved differences prevent choosing a single winner.
- Partial research is labeled as a partial answer. If no concise supported excerpt
  is found, the report says so and shows the findings and unresolved criteria.
- This bounded presentation is not general semantic understanding or independent
  source-truth verification. Original claim records and audits remain inspectable.

The app presentation and its Markdown download opt in to the new layout. Default
legacy/CLI rendering remains compatible. Existing saved compatible workbench runs
can display the new layout without new provider calls.

## Verification

Offline regressions cover both capital-statement word orders, noisy preceding
source text, source-number mapping, exact offsets, qualifier/decimal preservation,
relevant disagreement, unrelated differences and uncited evidence. Existing
report, source-download and UI tests are included in the focused checks.

The hosted build marker is **App version: 2026-10-16.2**. Full CI and hosted checks
are recorded after completion. Hosting remains free only.

## Measured verification

- The first focused run passed 40 tests in 312.35 seconds. After the final caution/typing fixes, all seven answer-focused cases passed in 63.38 seconds. Together these cover 41 unique focused tests (six cases overlap).
- Source commit 11e6f4c passed [full CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/runs/38856496552): **554 tests in 47.47 seconds**, strict checking of 89 source files, lint/format, packaging and constrained container checks.
- The new cases include preserving an explicit false-statement caution with its quotation rather than displaying the preceding sentence alone. They check exact spans, source-number mapping and unchanged canonical state.
- The public preflight did not observe version 2026-10-16.2 and submitted no research or demonstration request. No new Gemini or Tavily calls ran for this repair.
- The browser management connection timed out. An owner reboot was requested; hosted activation and the zero-provider-call offline ordering/download check remain pending.
