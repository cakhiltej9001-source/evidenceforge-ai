"""Report-only PDF downloads, with no provider calls or workflow-state changes."""

import html
import re
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Any

from evidenceforge.graph.state import ResearchState, StateSnapshot
from evidenceforge.reporting import render_report

_FONT_LOCK = Lock()
_INLINE = re.compile(
    r"(?<!\\)\*\*(.+?)(?<!\\)\*\*|(?<!\\)`([^`]+)`|"
    r"(?<!\\)\[((?:\\.|[^\]])+)\]\((https?://[^\s)]+)\)"
)


class PdfExportError(ValueError):
    """The report cannot be rendered faithfully with the installed PDF fonts."""


def _plain(text: str) -> str:
    return html.unescape(re.sub(r"\\([\\`*{}\[\]()#+.!_>|~\-])", r"\1", text))


def _inline(text: str) -> str:
    """Translate only the renderer's own bold/code/link syntax; escape source markup."""
    parts = []
    end = 0
    for match in _INLINE.finditer(text):
        parts.append(html.escape(_plain(text[end : match.start()])))
        bold, code, label, url = match.groups()
        if bold is not None:
            parts.append("<b>" + html.escape(_plain(bold)) + "</b>")
        elif code is not None:
            parts.append(html.escape(_plain(code)))
        else:
            parts.append(
                '<link href="'
                + html.escape(url, quote=True)
                + '" color="#175a8b">'
                + html.escape(_plain(label))
                + "</link>"
            )
        end = match.end()
    parts.append(html.escape(_plain(text[end:])))
    return "".join(parts)


def report_pdf(state: ResearchState) -> bytes:
    snapshot = StateSnapshot.model_validate(state)
    if snapshot.run_status.value in {"created", "running"}:
        raise PdfExportError("Finish the run before downloading its report.")
    return markdown_pdf(render_report(state, answer_first=True, include_evidence_details=False))


def markdown_pdf(markdown: str) -> bytes:
    """Lay out an already rendered report; does not reinterpret its recorded status."""
    if len(markdown.encode("utf-8")) > 2_000_000:
        raise PdfExportError("The report is too large for PDF export; use Markdown or JSON.")
    try:
        import reportlab
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError:
        raise PdfExportError("PDF export requires the UI dependencies.") from None

    with _FONT_LOCK:
        if "EvidenceForge" not in pdfmetrics.getRegisteredFontNames():
            fonts = Path(reportlab.__file__).parent / "fonts"
            for name, file in (("EvidenceForge", "Vera.ttf"), ("EvidenceForgeBold", "VeraBd.ttf")):
                pdfmetrics.registerFont(TTFont(name, str(fonts / file)))
            pdfmetrics.registerFontFamily(
                "EvidenceForge",
                normal="EvidenceForge",
                bold="EvidenceForgeBold",
                italic="EvidenceForge",
                boldItalic="EvidenceForgeBold",
            )
    supported = set(pdfmetrics.getFont("EvidenceForge").face.charToGlyph)
    if any(ord(char) not in supported for char in _plain(markdown) if not char.isspace()):
        raise PdfExportError(
            "Some characters are outside the PDF font's coverage. Use Markdown or JSON "
            "to preserve them."
        )

    body = ParagraphStyle(
        "Body",
        fontName="EvidenceForge",
        fontSize=10,
        leading=15.5,
        spaceAfter=7,
        textColor=colors.HexColor("#253244"),
        alignment=TA_LEFT,
        splitLongWords=True,
    )
    title = ParagraphStyle(
        "Title",
        parent=body,
        fontName="EvidenceForgeBold",
        fontSize=19,
        leading=24,
        spaceAfter=14,
        textColor=colors.HexColor("#143b59"),
        keepWithNext=True,
    )
    heading = ParagraphStyle(
        "Heading",
        parent=body,
        fontName="EvidenceForgeBold",
        fontSize=12,
        leading=17,
        spaceBefore=12,
        spaceAfter=7,
        keepWithNext=True,
    )
    bullet = ParagraphStyle("Bullet", parent=body, leftIndent=10, firstLineIndent=-7)
    code = ParagraphStyle("Code", parent=body, fontSize=7, leading=10, leftIndent=8)
    story: list[Any] = []
    fenced = False
    for line in markdown.splitlines():
        if line.startswith("```"):
            fenced = not fenced
            continue
        if not line.strip():
            continue
        if fenced:
            story.append(Paragraph(html.escape(line).replace(" ", "&#160;"), code))
        elif line.startswith("# "):
            story.append(Paragraph(_inline(line[2:]), title))
        elif line.startswith("## "):
            story.append(Paragraph(_inline(line[3:]), heading))
        elif line.startswith("- "):
            story.append(Paragraph("- " + _inline(line[2:]), bullet))
        else:
            story.append(Paragraph(_inline(line), body))
    story.append(Spacer(1, 8))
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=42,
        bottomMargin=44,
        title="EvidenceForge research report",
        author="EvidenceForge",
    )

    def footer(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("EvidenceForge", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(42, 25, "EvidenceForge | Saved research report")
        canvas.drawRightString(A4[0] - 42, 25, str(doc.page))
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
