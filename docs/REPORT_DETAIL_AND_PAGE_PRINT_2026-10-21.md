# Report detail and entire-page printing - 21 October 2026

## Changes

- Explicit inventory criteria need concrete named items in their linked retained evidence.
  A generic parent-list mention of mathematics and statistics cannot satisfy a request
  to list the mathematical and statistical foundations. Nearby lists for a different
  subject cannot supply that detail. Explicit item counts are respected.
- The structured Gemini coverage instruction asks for named foundations and separate
  support for each requested inventory. A conservative local check can withhold support
  and record a gap when a model assessment is too generous.
- Career progression excerpts receive the Career steps label. Concrete projects and
  intern/junior transitions take priority over unrelated salary and learning-duration
  assertions. Legitimate guidance such as earning a degree remains eligible.
- Exact display spans omit dangling next-item numbers and sentences with unresolved
  bibliography markers from the source website. Original quotations, offsets, source
  records and audits remain available.
- The concise Answer lists approved criteria for which no sufficiently specific, clean
  cited excerpt was selected. Reading an old saved report does not rewrite its recorded
  workflow status.

These are bounded structural and editorial checks. They do not certify source truth,
guarantee general semantic completeness, or add missing facts from model memory.

## Print or download the entire current Streamlit page

At the top of the workbench, select **Print entire page / Save as PDF**.
Choose **Save as PDF** as the browser print destination.

This prints the current session from the question through progress, Answer, Key Findings,
sources, retained passages, and audit sections. Expandable sections open for printing;
nested JSON has a full text print copy, and long text fields are printed without their
scroll limits. The sections return to their earlier state after the print dialog closes.

The export covers the current page. Other saved runs and original uploaded files are
separate. The concise **Download report PDF**, Markdown and JSON downloads remain available.
Use the concise PDF when sharing the research report; use the full-page print when
documenting the app session and its inspection records.

Printing and downloading do not start Gemini, Tavily or LangSmith calls. Hosting remains
free only.

## Verification

- 27 focused offline regression cases passed, including the supplied failure patterns,
  exact span preservation, state immutability, degree guidance, and escaping nested print data.
- Complete lint gate passed.
- Strict type checking passed for 93 source files; formatting passed for all 231 Python files.
- An isolated synthetic Streamlit report passed the real-browser print test in Edge: four
  collapsed sections opened for printing and returned to their prior state; long question
  text used a print copy; no JavaScript errors occurred.
- The resulting nine-page PDF contained the title/question, report, sources, nested audit
  data and final page text. Printed pages were rendered for visual inspection.
- Full source and container checks run in [GitHub CI](https://github.com/cakhiltej9001-source/evidenceforge-ai/actions/workflows/ci.yml)
  for the published commit; inspect that run for its final outcome.

No new provider calls were used for this repair. Offline fixture tests do not establish
a new successful live Gemini/Tavily run. The original user exports are private and unchanged.

## Implementation references

- [Streamlit HTML API](https://docs.streamlit.io/1.56.0/develop/api-reference/text/st.html):
  fixed application JavaScript is allowed explicitly; report/source text is never interpolated
  into executable HTML.
- [Browser print](https://developer.mozilla.org/en-US/docs/Web/API/Window/print) and
  [beforeprint](https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeprint_event):
  the page prepares its full print layout and restores its view after printing.
