# Read saved source passages when an original website is blocked

## Diagnosis

The reported URL, https://www.globalelectricity.org/solar-vs-wind-energy/,
returned HTTP 403 to direct requests. The ordinary non-www variant returned 403
too. This is an access response from the publisher's site; changing the link text
cannot remove it. A search provider may retain text even when browser access is
blocked. Access can vary between clients.

## App change

- Source titles and citation numbers inside the app open **Saved source passages**.
- A separate **Original website** link preserves the original citation URL.
- The viewer reads only evidence cited by the final report, from its already
  owner-scoped state. It fetches no website and makes no model/search calls.
- **Download saved passages [n]** exports the exact cited text, original URL,
  provider, acquisition times, retained content scope and passage locators.
- Search/section excerpts are labeled. Retained passages are not represented as a
  complete article, current website access or independent proof of source truth.
- Downloaded Markdown keeps original URLs and explains the saved-evidence fallback;
  JSON and text downloads retain the inspected passage text.

The change also applies when reopening an existing compatible saved run. It does
not replace sources with unrelated working URLs or bypass the publisher's access
controls. No fresh Gemini or Tavily allowance is needed to read existing evidence.

## Deployment

The hosted build marker is **App version: 2026-10-16.1**. Source and UI regressions
run with networking blocked, including exact Unicode/markup preservation, exclusion
of uncited evidence, safe title rendering, local anchors and real text downloads.
Full CI and hosted activation are recorded after verification; the publisher's
original 403 response remains outside the app's control. Hosting remains free only.
