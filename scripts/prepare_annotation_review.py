"""Prepare a local form for a person to review all frozen benchmark labels."""

import argparse
import html
import json
import re
from pathlib import Path

from evidenceforge.evaluation import load_dataset

PAGE = r"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EvidenceForge annotation review</title>
<style>body{font:16px/1.6 system-ui;max-width:1000px;margin:32px auto;padding:0 24px;
background:#f4f7fa;color:#172534}section{background:white;border:1px solid #d3dce5;
border-radius:10px;padding:20px;margin:20px 0}pre{white-space:pre-wrap;font:inherit}
input,select,textarea,button{font:inherit;padding:8px;box-sizing:border-box}
textarea{width:100%;min-height:90px}label{display:block;margin:10px 0}
.notice{padding:12px;background:#fff0c5}button{cursor:pointer}#status{font-weight:bold}</style>
<h1>Review the 20 benchmark labels</h1>
<p class="notice">These synthetic labels were drafted by Codex. An independent person
must inspect every case, including the retained evidence and expected dispute/abstention.
This page collects your decisions locally. It does not certify identity or change the dataset.</p>
<p>Dataset SHA-256: <code>__DIGEST__</code></p>
<form id="review"><section><label>Reviewer name <input name="reviewer" required></label>
<label>Review date <input name="date" type="date" required></label>
<label><input name="attestation" type="checkbox" required>
I am a human reviewer and independently checked each case against its synthetic corpus.</label>
</section>__SECTIONS__
<p id="status">0 of 20 decisions recorded.</p>
<button type="submit">Download review decisions</button>
</form>
<p>A revision needs an explanation. The exported JSON is a review record, not an approved
replacement dataset. Review revisions and freeze a new dataset version before rerunning
benchmarks. No decisions are preselected; leaving this page loses unsaved decisions.</p>
<script>
'use strict';
const form = document.querySelector('#review');
const sections = [...form.querySelectorAll('section[data-case]')];
form.addEventListener('input', () => {
  const reviewer = form.elements.namedItem('reviewer');
  reviewer.setCustomValidity(reviewer.value.trim() ? '' : 'Enter the reviewer name.');
  const count = sections.filter(s => s.querySelector('select').value).length;
  document.querySelector('#status').textContent =
    `${count} of ${sections.length} decisions recorded.`;
  for (const section of sections) {
    const notes = section.querySelector('textarea');
    notes.required = section.querySelector('select').value === 'revise';
    notes.setCustomValidity(notes.required && !notes.value.trim()
      ? 'Explain the requested revision.' : '');
  }
});
form.addEventListener('submit', event => {
  event.preventDefault();
  const reviewer = form.elements.namedItem('reviewer');
  reviewer.setCustomValidity(reviewer.value.trim() ? '' : 'Enter the reviewer name.');
  if (!form.reportValidity()) return;
  const cases = sections.map(section => ({
    case_id:section.dataset.case,
    decision:section.querySelector('select').value,
    notes:section.querySelector('textarea').value.trim()
  }));
  const result = {
    record_type:'human_annotation_review_decisions',
    dataset_sha256:'__DIGEST__',
    reviewed_by:reviewer.value.trim(),
    reviewed_at:form.elements.namedItem('date').value,
    human_review_attestation:form.elements.namedItem('attestation').checked,
    overall_status:cases.some(c => c.decision === 'revise')
      ? 'revisions_required' : 'all_cases_approved',
    cases
  };
  const blob = new Blob([JSON.stringify(result,null,2)],{type:'application/json'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href=url;
  link.download='annotation-review-decisions.json';
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url),1000);
});
</script></html>
"""


def prepare(dataset_path: Path, packet_path: Path, output: Path) -> None:
    dataset, digest = load_dataset(dataset_path)
    packet = packet_path.read_text(encoding="utf-8-sig")
    if f"Dataset SHA-256: `{digest}`" not in packet:
        raise ValueError("Review packet does not match the frozen dataset")
    matches = re.findall(r"^## (diverse_\d+)[^\n]*\n(.*?)(?=^## |\Z)", packet, re.M | re.S)
    packets = {case_id: body.split("Reviewer decision:", 1)[0] for case_id, body in matches}
    if len(matches) != len(dataset.cases) or set(packets) != {case.id for case in dataset.cases}:
        raise ValueError("Review packet must contain each dataset case exactly once")
    sections = []
    for case in dataset.cases:
        section = (
            f'<section data-case="{html.escape(case.id, quote=True)}">'
            f"<h2>{html.escape(case.id)} — {html.escape(case.split)}</h2>"
            f"<pre>{html.escape(packets[case.id].strip())}</pre>"
            '<label>Decision <select required><option value="">Choose after reviewing</option>'
            '<option value="approve">Approve the draft label</option>'
            '<option value="revise">Request a revision</option></select></label>'
            "<label>Review notes <textarea></textarea></label></section>"
        )
        sections.append(section)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        PAGE.replace("__DIGEST__", digest).replace("__SECTIONS__", "\n".join(sections)),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"output": str(output.resolve()), "cases": len(sections), "dataset_sha256": digest}
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=Path("docs/evaluation/diverse_dataset.json")
    )
    parser.add_argument("--packet", type=Path, default=Path("docs/evaluation/ANNOTATION_PACKET.md"))
    parser.add_argument(
        "--output", type=Path, default=Path(".evidenceforge/review/phase9/index.html")
    )
    args = parser.parse_args()
    prepare(args.dataset, args.packet, args.output)
