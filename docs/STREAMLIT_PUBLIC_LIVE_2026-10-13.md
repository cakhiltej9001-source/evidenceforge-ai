# Public live research without a password - 13 October 2026

The owner explicitly requested removing the app password after enabling live
research. Community Cloud live mode now defaults to public access; the existing
Gemini and Tavily keys remain in private Streamlit secrets.

- No sign-in is required. Configured Gemini and Tavily are selected by default.
- Each browser session receives a server-generated visitor scope. Visitors cannot
  choose the previous owner scope, list another visitor's runs or reuse their
  document IDs. Existing owner records are not promoted into a visitor scope.
- Limits remain at most 6 Gemini calls and 1 Tavily search per hosted run.
  These are per-run limits, not a lifetime allowance. Public requests consume
  the configured provider credits. No provider call is made merely by opening
  the page; Create plan and plan approval remain explicit actions.
- Hosting remains free and hosted storage remains temporary. Download reports.
- To restore login later, explicitly set EVIDENCEFORGE_CLOUD_ACCESS to login in
  Streamlit secrets. Public is the default and clears a prior forced login flag.

Offline tests cover removal of the old login flag, optional login, separate
public visitor scopes, configured live defaults and secret redaction. No new
Gemini or Tavily requests were made while removing the password.

Earlier login-protected deployment records remain historical. Hosted activation
is checked separately from source tests and GitHub CI.
