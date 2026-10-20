# Editorial repair and report-only PDF - 20 October 2026

App version: **2026-10-20.2**.

## Changes

- Highlight filters now catch named course-provider benefit wording, including
  possessive provider names followed by course descriptions. Neutral mentions of
  education or coursework remain eligible.
- Dependent answers beginning with words such as "Yes, because" and page-header
  material are omitted from highlights. Mixed FAQ passages can supply exact,
  independently readable excerpts; the original source remains retained.
- Explicit, consecutive numbered sections with independent headings can be shown
  separately. Qualifications, including contractions, remain with their item.
  Ordinary paragraphs cannot be split this way to discard a caveat.
  Display-only formatting issues do not remove the full evidence from model
  assessment; promotional and existing evidence-quality guards still apply.
- Approved topic matching admits concrete project examples, explicit framework
  lists and career-entry guidance without requiring repetition of the whole
  research question. Once topic selections are available, unrelated filler is
  not appended just to fill five answer slots.
- Highlighted findings use **Finding 1, Finding 2, ...** in displayed order.
  Original claim IDs, quotation offsets and citation records are unchanged.
- The workbench offers **Download report PDF**. It contains the question, answer,
  findings, source links and limitations, without app controls or inspection JSON.
  The PDF embeds its fonts and preserves searchable text and clickable links.
- Markdown downloads and the on-screen source list omit long evidence identifiers.
  Detailed offsets, snapshots and audit records remain available separately.

## Verification and scope

Targeted offline regressions cover promotions, missing context, numbered lists,
topic selection, sequential labels, exact offsets, immutability and PDF downloads.
The existing UI download test also checks the PDF file delivered by Streamlit.
Full source CI is verified after publication.

A presentation-only replay of the supplied completed report selected all five
approved topic areas. It removed the named-course pitch, dependent FAQ answer and
publication header from highlights. The private original files were unchanged.
A clean PDF was generated and visually checked locally; those user files are not
published in this repository.

This repair made **zero Gemini, Tavily or LangSmith calls**. It does not represent
a fresh model evaluation, independent human review or source-truth verification.
Historical run statuses, budgets, receipts and source snapshots are not rewritten.

## Limits

These are conservative editorial heuristics. Exact quotation checks do not prove
the quoted advice is correct or establish universal job requirements. PDF export
reports a font-coverage limitation instead of silently corrupting unsupported
characters; Markdown and JSON preserve the original text in that case.

PDF layout uses the official [ReportLab paragraph](https://docs.reportlab.com/reportlab/userguide/ch6_paragraphs/)
and [document layout](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/)
interfaces. The UI dependency and Streamlit requirements are pinned through the
project lock file.
