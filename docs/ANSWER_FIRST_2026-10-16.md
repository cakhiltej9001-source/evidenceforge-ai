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
