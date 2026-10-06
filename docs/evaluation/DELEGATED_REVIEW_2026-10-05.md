# Benchmark review on the user's behalf — 5 October 2026

**Delegated review completed for all 20 cases.** Reviewer: Codex (AI), acting on
the user's explicit request. This records actual review work, without attributing
a human attestation or independent reviewer identity to the user.

## Decision

Use the frozen benchmark for synthetic workflow checks. Request revisions to the
scope of 16 questions before using them for research-quality conclusions. Retain
the two numeric-dispute labels and two empty-corpus abstention labels. General
research-quality sign-off is withheld because scope, evidence access and scoring
still differ. This review is complete; the remaining work is benchmark correction
and a fair comparison, rather than repeating the same delegated review request.

The original dataset and all historical results remain unchanged. Dataset SHA-256:
`5e5c012fd1a612513a934e30469ba5a20b532e909732cfd47500f8453cdf4e89`.
The loader's original `draft_requires_human_review` marker is preserved; a factual
claim of independent human validation is not made.

## Evidence checked

- All 20 case questions, reference passages, expected labels and fixture corpora.
- All **40 saved fixture runs**: recomputed every row against its saved state;
  all metrics matched. All four partition/variant aggregate summaries matched.
- **124 artifact hash/byte-count checks** and **62 exact passage-offset checks**
  passed. These count retained records across runs, not independent sources.
- All **20 usable paid one-shot responses** were inspected from preserved original
  and extension results. Two dispute answers lacked the synthetic records and
  declined or qualified their answer; the two empty-source cases supplied uncited
  general-knowledge claims. These are evidence-access observations, not truth grades.
- No new Gemini, Tavily, NESO or Render requests; original allowance 26/30 and
  extension allowance 28/40 unchanged. No benchmark run was repeated.

## Findings and corrections

1. **Question scope (16 cases).** Questions ask to compare outputs, while sources
   only state dependencies. They do not support quantities, common units, efficiency
   comparisons or broad performance conclusions. A scripted planner narrows these
   questions to dependency retrieval; real planning can reasonably request broader
   evidence. Proposed narrow questions are recorded below. A new versioned dataset
   must be frozen before execution; these proposals have not been benchmarked.
2. **Scripted retrieval schedule.** The custom fixture exposes one passage per pass
   and releases the second passage on a later pass. Better coverage with more passes
   demonstrates recovery under that schedule. It does not measure a model's research
   skill, source discovery or superiority over another provider.
3. **Fair evidence access.** The one-shot Gemini baseline receives the question but
   no frozen corpus. The corpus-bound workflow receives synthetic passages. Uncited
   baseline metrics remain N/A; treating them as zero would create an unfair score.
   A future comparison must specify a common evidence-access policy or report the
   different tasks separately.
4. **Small and reused evaluation cases.** The two disputes share the same Northfield
   corpus and are not independent problem settings. Empty-source success has only two
   cases. The development/held-out labels reflect the historical partition, but the
   cases have now been inspected and used in repair diagnostics. Fresh unseen cases
   are needed for future claims of generalization.
5. **Scoring limits.** Exact-string reference recovery and exact quotation support
   establish mechanical fidelity, not semantic quality, relevance or source truth.
   Abstention must be judged against the evidence available to that task. Dollar
   costs and uncaptured historical latency remain N/A.

## Case decisions and proposed wording

| Case | Decision | Proposed question / retained label |
|---|---|---|
| diverse_01 | Revise question scope | According to the supplied synthetic passages, what stated factors affect solar and wind output? |
| diverse_02 | Revise question scope | According to the supplied synthetic passages, what stated factors affect hydro and geothermal output? |
| diverse_03 | Revise question scope | According to the supplied synthetic passages, what stated factors affect battery storage and hydrogen storage output? |
| diverse_04 | Revise question scope | According to the supplied synthetic passages, what stated factors affect rail and bus output? |
| diverse_05 | Revise question scope | According to the supplied synthetic passages, what stated factors affect LED lighting and heat pumps output? |
| diverse_06 | Revise question scope | According to the supplied synthetic passages, what stated factors affect desalination and water recycling output? |
| diverse_07 | Revise question scope | According to the supplied synthetic passages, what stated factors affect insulation and reflective roofing output? |
| diverse_08 | Revise question scope | According to the supplied synthetic passages, what stated factors affect radar and satellite sensing output? |
| diverse_09 | Revise question scope | According to the supplied synthetic passages, what stated factors affect tree planting and cool pavement output? |
| diverse_10 | Revise question scope | According to the supplied synthetic passages, what stated factors affect fiber networks and wireless networks output? |
| diverse_11 | Revise question scope | According to the supplied synthetic passages, what stated factors affect composting and landfill disposal output? |
| diverse_12 | Revise question scope | According to the supplied synthetic passages, what stated factors affect tidal and wave output? |
| diverse_13 | Revise question scope | According to the supplied synthetic passages, what stated factors affect drip irrigation and flood irrigation output? |
| diverse_14 | Revise question scope | According to the supplied synthetic passages, what stated factors affect local caching and remote queries output? |
| diverse_15 | Revise question scope | According to the supplied synthetic passages, what stated factors affect retrieval and fine-tuning output? |
| diverse_16 | Revise question scope | According to the supplied synthetic passages, what stated factors affect ventilation and filtration output? |
| diverse_17 | Retain fixture label | Dispute: same-scope 100 versus 120 GWh; equivalent-unit/copy/different-year records kept distinct. |
| diverse_18 | Retain fixture label | Dispute: same-scope 100 versus 120 GWh; equivalent-unit/copy/different-year records kept distinct. |
| diverse_19 | Retain fixture label | Abstain from factual claims because no source is available. |
| diverse_20 | Retain fixture label | Abstain from factual claims because no source is available. |

The [machine-readable review](DELEGATED_REVIEW_2026-10-05.json) includes each
case's source passages, reasons, proposed question and verified saved-run outcomes.
The 16 reference passage values are retained as dependency statements, not treated
as a complete answer to the original broad comparison.

## Next work

Freeze narrower or richer cases with explicit answer criteria, cover more independent
problem settings, and define common evidence access plus semantic assessment. Verify
any changed planner/scorer protocol separately. Run future variants into a new output
directory using a new manifest and an explicitly applicable provider budget. Do not
relabel the historical results as measurements of the current source or new proposals.
Human validation may be added by a real independent reviewer if that claim is needed.
Hosting deployment and production improvements are separate tasks and are not approved
or completed by this benchmark review.
