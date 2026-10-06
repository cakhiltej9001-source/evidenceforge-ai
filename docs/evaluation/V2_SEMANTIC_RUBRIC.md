# Corrected v2 comparison rubric

This rubric is for reviewing saved answers in
`.evidenceforge/evaluation/phase9_v2_gemini/` if the paid comparison can run.
It does not assign factual truth to the synthetic corpus.

For each case and variant, record:

1. **Scope:** every requested aspect is addressed, or the answer explicitly
   abstains when the frozen corpus is insufficient.
2. **Citation identity:** every claim cites only source IDs supplied to that
   answer.
3. **Quotation fidelity:** quoted claims reproduce complete source sentences;
   do not reward paraphrases as exact quotations.
4. **Qualification fidelity:** factors, conditions, dates, units and uncertainty
   are retained when they appear in the source passage.
5. **Conflict handling:** conflicting values for the same entity, metric, date
   and scope are marked as disputed; the answer must not guess a resolution.
6. **Unsupported content:** claims absent from the supplied corpus are errors,
   even when they sound generally plausible.

Use `pass`, `revise` or `fail` per dimension, with a short reason and reviewer
identity/date. A Codex review is an AI review; an independent human sign-off
requires a separate reviewer record.
