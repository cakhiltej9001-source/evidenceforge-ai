# Real research requires real sources

## Reported issue

The user asked for the capital of Telangana with Gemini selected but Tavily
unchecked, no energy API and no imported document. The earlier UI silently chose
an energy fixture. Gemini could not produce supported claims from those examples,
so the report correctly stopped with insufficient evidence. No real web search ran.

## Fix

- The workbench defaults to **Research with real sources**.
- If no document, web search or energy API is selected, Create plan displays a
  specific source-selection error before calling the workbench. That submission
  makes no model or search calls.
- Synthetic scenarios appear only after explicitly choosing **Synthetic
  demonstration**. That mode uses offline reasoning and excludes documents/live
  sources from the request.
- Real-source mode explains that Gemini does not search the web by itself.
- The cloud entrypoint displays **App version: 2026-10-15.1**. Its dependency
  manifest includes a deployment refresh marker to request a fresh environment.
  Streamlit documents [automatic dependency resolution after manifest changes](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/upgrade-streamlit).

## How to run the question

1. Open the [public app](https://evidenceforge-ai-akhiltej.streamlit.app/).
2. Select **Research with real sources** and enter **What is the capital of Telangana?**
3. Select Gemini and check **Search live web with Tavily**.
4. Create, review and approve the plan. This consumes the configured provider allowance.

The expected factual answer is Hyderabad, as stated by the
[Hyderabad district government](https://hyderabad.telangana.gov.in/about-district/).
That external check is not presented as a new Gemini/Tavily app run.

## Verification boundaries

Regression tests check that source-free submissions never reach the workbench,
with both Gemini and offline reasoning, while explicitly selected web/documents
reach it correctly. Existing demonstrations and recovery flows remain covered.
No new Gemini, Tavily or LangSmith calls are needed to verify this UI guard.
Earlier failed runs and provider receipts are preserved. Hosting remains free only.

Hosted activation is checked separately with a fresh browser: the check requires
the new mode control and version before attempting a source-free submission.
It never submits a paid research request on an older build.
