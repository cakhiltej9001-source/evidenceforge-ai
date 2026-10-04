# Delegated AI annotation review — 4 October 2026

Reviewer: Codex (AI), following the user instruction to act on their behalf.
Dataset SHA-256: `5e5c012fd1a612513a934e30469ba5a20b532e909732cfd47500f8453cdf4e89`

All 20 cases were reviewed. This record is an AI review. The frozen dataset remains a draft; no human name, human attestation or human approval was supplied.

The reference labels are internally consistent for synthetic workflow checks. The first 16 questions describe outputs broadly, while their evidence gives only dependencies. A real quality benchmark needs narrower questions or richer frozen corpora and review of the matching/scoring policy. Changing questions or labels requires a new dataset version and rerunning its variants; existing results are retained.

| Case | Decision | Reason |
|---|---|---|
| diverse_01 | qualified_for_synthetic_workflow_only | The passages identify sunlight and wind speed. They contain no electricity amount, capacity factor, location or interval; the broad outputs question invites a quantitative plan the corpus cannot answer. |
| diverse_02 | qualified_for_synthetic_workflow_only | Water flow and subsurface heat are explicit dependencies. No generation quantities or comparative efficiency are supplied. |
| diverse_03 | qualified_for_synthetic_workflow_only | Charge cycles and conversion efficiency are retained statements. Stored energy, discharge power and conversion yield are distinct outputs and need a stated metric for real research. |
| diverse_04 | qualified_for_synthetic_workflow_only | Electrification and fleet scheduling are explicit fixture dependencies. Rail and bus outputs lack a common outcome or unit; these labels only test retrieval of two statements. |
| diverse_05 | qualified_for_synthetic_workflow_only | Electrical supply and ambient temperature appear in the corpus. Lighting and heat-pump outputs have different units, so this is a dependency comparison only. |
| diverse_06 | qualified_for_synthetic_workflow_only | Membrane pressure and treatment stages are stated. Water yield, quality and recovery rate are absent; the corpus supports the two qualitative statements only. |
| diverse_07 | qualified_for_synthetic_workflow_only | Thermal resistance and surface reflectance are stated. No temperature or energy-saving comparison can be inferred. |
| diverse_08 | qualified_for_synthetic_workflow_only | Signal reflections and orbital coverage are stated. These do not establish comparable sensing accuracy, spatial resolution or output quantity. |
| diverse_09 | qualified_for_synthetic_workflow_only | Canopy growth and surface material are stated. No cooling magnitude, period or urban context is supplied. |
| diverse_10 | qualified_for_synthetic_workflow_only | Cable capacity and radio spectrum are stated. Throughput, latency and operating conditions are absent. |
| diverse_11 | qualified_for_synthetic_workflow_only | Organic feedstock and waste containment are stated. The question does not define whether output means material, emissions or disposal performance. |
| diverse_12 | qualified_for_synthetic_workflow_only | Tidal range and wave motion are stated. No electricity generation or capacity comparison is available. |
| diverse_13 | qualified_for_synthetic_workflow_only | Delivery pressure and field runoff are stated. Yield, water delivery and efficiency are unspecified; the live planner expanded beyond these two references. |
| diverse_14 | qualified_for_synthetic_workflow_only | Cache freshness and network latency are stated. Result correctness and response performance are different metrics, and no measured values are supplied. |
| diverse_15 | qualified_for_synthetic_workflow_only | Indexed sources and training data are stated. The corpus cannot compare answer quality or define equivalent retrieval and fine-tuning outputs. |
| diverse_16 | qualified_for_synthetic_workflow_only | Air exchange and filter media are stated. No comparable pollutant removal or airflow figures are provided. |
| diverse_17 | dispute_label_supported_by_fixture | The two independent synthetic sources report 100 and 120 GWh for the same entity, year, population and condition: a valid numeric dispute. 100000 MWh equals 100 GWh; 900 GWh concerns 2023; the copied 100 GWh source is not independent. |
| diverse_18 | dispute_label_supported_by_fixture | The same 100 versus 120 GWh conflict supports the dispute label. Unit conversion, different-year evidence and copied-source provenance must retain their separate relationships. |
| diverse_19 | abstention_label_supported_by_empty_fixture | The fixture returns no source. Empty references and abstention are consistent for evidence-grounded output; a general-knowledge answer has no retained-source support. |
| diverse_20 | abstention_label_supported_by_empty_fixture | The fixture returns no source. Empty references and abstention are consistent; no rainfall or river-flow facts can be verified from this corpus. |

Exact-string reference matching measures recovered quotations, not semantic truth. The general-knowledge one-shot baseline and a corpus-bound agent have different access to evidence; citation and support scores need their stated denominators and qualifications. No provider superiority or assignment compliance is established by this review.
