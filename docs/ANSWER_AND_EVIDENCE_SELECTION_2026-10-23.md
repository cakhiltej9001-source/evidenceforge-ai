# Answer and evidence selection repair - 23 October 2026

## What failed

The 21 October live test of "How to become an AI engineer?" used four successful
Gemini calls and one successful Tavily search. The critic approved the report and
15 quotation checks passed, but the report correctly remained partial: four of
five planned criteria had support. The mathematics criterion was unresolved.

Two selection defects were found by inspecting the saved run:

- An author introduction repeated "programming languages" and "frameworks", so
  lexical matching selected the biography as programming guidance.
- The saved full-text source included concrete mathematics material, but the
  bounded passage selector favored generic skill mentions and data-structure
  text. It did not equate "mathematical" with "mathematics", and words from a
  criterion's purpose clause outweighed its requested subject.

## Repair

- Author biographies are excluded from highlighted career answers and findings.
  Their original passages remain available. Explicit questions about an author
  can still use biographical material.
- A compound language/framework criterion can display separate exact, audited
  quotations for its two parts. Unicode styling is normalized only for matching;
  quotations and source offsets retain their original characters.
- Independent bullet headings stay with their descriptions. A governing caveat
  prevents splitting the original passage.
- Passage ranking prioritizes the requested subject and concrete inventory
  detail before purpose-clause word overlap. Existing extraction limits remain.
- Criteria phrased as mathematical "concepts" receive the same concrete-detail
  safeguard as criteria phrased as "foundations".

## Verification and limits

The actual extractor was replayed offline against the saved source artifacts. It
now retains the concrete mathematics passage with its qualification intact,
within the unchanged 40-passage/5-source limits. The original state hash matched
before and after the replay. No new coverage assessment or final report was invented.

Extraction and existing retrieval regressions passed 29 cases. Additional answer
and coverage regressions exercise the reported defects; source and container gates run in [GitHub CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/workflows/ci.yml).
The original saved run, its receipts, source artifacts, status and gaps are unchanged.
No new Gemini, Tavily or LangSmith calls are part of this repair's offline checks.

This is not a fresh successful live workflow. Improved extraction makes relevant
material available to the coverage evaluator on a new run; it does not itself
establish semantic sufficiency, certify source truth, or upgrade an old report.

The hosted version marker for this repair is **2026-10-23.1**. A GitHub push does
not by itself prove that Streamlit has loaded that version.
