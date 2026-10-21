"""Trusted browser controls for printing the current Streamlit session."""

import json
from html import escape


def json_print_html(value: object) -> str:
    """A non-executable print copy includes nested JSON hidden by tree widgets."""
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    return '<pre class="ef-print-json">' + escape(text) + "</pre>"


# This is fixed application code. Never interpolate questions, sources, uploaded
# documents, credentials or model output into the executable HTML below.
PAGE_PRINT_HTML = r"""
<style>
#ef-page-print {font:inherit; color:inherit; background:transparent;
  border:1px solid #80808080; border-radius:.5rem; padding:.55rem .9rem;
  cursor:pointer; margin-bottom:.3rem;}
#ef-page-print:hover {border-color:#ff4b4b; color:#ff4b4b;}
.ef-print-value, .ef-print-json {display:none;}
@media print {
  @page {size:auto; margin:12mm;}
  html, body, #root, [data-testid="stApp"], [data-testid="stAppViewContainer"],
  [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
    height:auto !important; max-height:none !important; min-height:0 !important;
    overflow:visible !important; position:static !important;
  }
  [data-testid="stMainBlockContainer"] {padding:0 !important; max-width:none !important;}
  [data-testid="stMain"] {display:block !important;}
  [data-testid="stMain"] * {
    color:#111 !important; background-color:#fff !important;
    box-shadow:none !important; text-shadow:none !important;
    overflow:visible !important; max-height:none !important;
  }
  [data-testid="stMain"] a {color:#1253a0 !important; text-decoration:underline;}
  [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"],
  [data-testid="stBottom"], #ef-page-print, #ef-page-print-help,
  [data-testid="stElementToolbar"], [data-testid="stDownloadButton"] {display:none !important;}
  .ef-print-value {display:block !important; white-space:pre-wrap;
    overflow-wrap:anywhere; border:1px solid #ddd; padding:.5rem;}
  textarea[data-ef-print-hidden] {display:none !important;}
  [data-testid="stJson"] {display:none !important;}
  .ef-print-json {display:block !important; font-size:9pt;}
  pre, code {white-space:pre-wrap !important; overflow-wrap:anywhere !important;}
  h1, h2, h3, summary {break-after:avoid;}
  p, li {orphans:3; widows:3;}
}
</style>
<button id="ef-page-print" type="button">Print entire page / Save as PDF</button>
<p id="ef-page-print-help" style="font-size:.875rem;opacity:.75;margin:.2rem 0 .8rem">
Save this session from top to bottom, including its expandable sections.
Choose Save as PDF in the print dialog. Other saved runs and original uploaded files
are separate. For a concise export, use Download report PDF below the report.
</p>
<script>
(() => {
  window.evidenceForgePagePrint?.dispose();
  const button = document.getElementById("ef-page-print");
  let closed = [], mirrors = [], prepared = false;
  function prepare() {
    if (prepared) return;
    prepared = true;
    const main = document.querySelector('[data-testid="stMain"]') || document.body;
    closed = [...main.querySelectorAll("details:not([open])")];
    closed.forEach(element => { element.open = true; });
    main.querySelectorAll("textarea").forEach(element => {
      const value = document.createElement("div");
      value.className = "ef-print-value";
      value.textContent = element.value || element.placeholder || "(empty)";
      element.setAttribute("data-ef-print-hidden", "");
      element.after(value);
      mirrors.push([element, value]);
    });
  }
  function restore() {
    closed.forEach(element => { element.open = false; });
    mirrors.forEach(([element, value]) => {
      element.removeAttribute("data-ef-print-hidden"); value.remove();
    });
    closed = []; mirrors = []; prepared = false;
  }
  function printPage() {
    prepare();
    requestAnimationFrame(() => {
      try { window.print(); } catch (error) { restore(); throw error; }
    });
  }
  button.addEventListener("click", printPage);
  window.addEventListener("beforeprint", prepare);
  window.addEventListener("afterprint", restore);
  window.evidenceForgePagePrint = {dispose() {
    restore();
    button.removeEventListener("click", printPage);
    window.removeEventListener("beforeprint", prepare);
    window.removeEventListener("afterprint", restore);
  }};
})();
</script>
"""
