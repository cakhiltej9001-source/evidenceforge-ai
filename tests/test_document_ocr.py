"""Local OCR, page disclosure and DOCX relationship regressions."""

import asyncio
import importlib.util
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from docx import Document
from pypdf import PdfReader, PdfWriter

from evidenceforge.exports import report_export
from evidenceforge.reporting import OCR_TRANSCRIPT_LIMITATION, render_report
from evidenceforge.schemas import ResearchRequest
from evidenceforge.services.research import ResearchService
from evidenceforge.storage import ocr as local_ocr
from evidenceforge.storage.documents import DocumentOptions, DocumentStore
from evidenceforge.storage.ocr import LocalOcrFailure, OcrLimits, transcribe_pdf


def blank_pdf(path, pages=2):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    writer.write(path)


def test_docx_table_row_keeps_entity_value_and_unit_together(tmp_path):
    document = Document()
    table = document.add_table(rows=3, cols=3)
    for row, values in zip(
        table.rows,
        [("Technology", "Output", "Unit"), ("Solar", "123", "GWh"), ("Wind", "456", "GWh")],
        strict=True,
    ):
        for cell, value in zip(row.cells, values, strict=True):
            cell.text = value
    path = tmp_path / "table.docx"
    document.save(path)
    store = DocumentStore(tmp_path / "documents")
    record = store.ingest(path)
    solar = store.search("local", (record.id,), "Solar GWh", 1)[0]
    assert solar.text == "Solar | 123 | GWh"
    assert solar.section == "table 1, row 2, columns 1-3"
    assert "456" not in solar.text
    assert record.parser_version == "located_document_v2"


def test_disabled_ocr_never_runs_a_worker(tmp_path, monkeypatch):
    path = tmp_path / "scan.pdf"
    blank_pdf(path)
    monkeypatch.setattr(
        "evidenceforge.storage.documents.transcribe_pdf",
        lambda *_: pytest.fail("OCR must be explicitly enabled"),
    )
    record = DocumentStore(tmp_path / "documents").ingest(path)
    assert record.status == "textless"
    assert len(record.warnings) == 2


def test_enabled_ocr_preserves_locators_discloses_and_limits_pages(tmp_path, monkeypatch):
    path = tmp_path / "scan.pdf"
    blank_pdf(path, pages=3)
    seen = []

    def ocr(data, pages, limits, root):
        seen.append(pages)
        return {1: "Solar generation is 123 GWh."}

    monkeypatch.setattr("evidenceforge.storage.documents.transcribe_pdf", ocr)
    store = DocumentStore(
        tmp_path / "documents",
        DocumentOptions(enable_ocr=True, ocr=OcrLimits(max_pages=1)),
    )
    record = store.ingest(path)
    assert seen == [(1,)]
    assert record.status == "partial"
    assert "OCR transcript" in record.warnings[0]
    assert "page limit" in record.warnings[1]
    chunk = store.chunks("local", record.id)[0]
    assert chunk.page == 1 and chunk.section == "local OCR transcription"
    assert chunk.text == "Solar generation is 123 GWh."
    assert chunk.end_offset - chunk.start_offset == len(chunk.text)


def test_unavailable_ocr_is_reported_without_inventing_evidence(tmp_path, monkeypatch):
    path = tmp_path / "scan.pdf"
    blank_pdf(path)

    def unavailable(*_):
        raise LocalOcrFailure("Local OCR requires Python 3.12 and the optional ocr extra.")

    monkeypatch.setattr("evidenceforge.storage.documents.transcribe_pdf", unavailable)
    record = DocumentStore(tmp_path / "documents", DocumentOptions(enable_ocr=True)).ingest(path)
    assert record.status == "textless" and record.chunk_count == 0
    assert all("requires Python 3.12" in warning for warning in record.warnings)


def test_ocr_worker_paths_use_resolved_dependencies_without_ambient_search_paths(
    tmp_path, monkeypatch
):
    rapid_root = tmp_path / "rapid-installation"
    pdfium_root = tmp_path / "pdfium-installation"
    specs = {
        "rapidocr_onnxruntime": importlib.util.spec_from_file_location(
            "rapidocr_onnxruntime", rapid_root / "rapidocr_onnxruntime" / "__init__.py"
        ),
        "pypdfium2": importlib.util.spec_from_file_location(
            "pypdfium2", pdfium_root / "pypdfium2.py"
        ),
    }
    monkeypatch.setattr(importlib.util, "find_spec", specs.get)
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "untrusted"))
    assert local_ocr._worker_pythonpath().split(os.pathsep) == [
        str(Path(local_ocr.__file__).resolve().parents[2]),
        str(rapid_root.resolve()),
        str(pdfium_root.resolve()),
    ]


@pytest.mark.parametrize(
    "platform, tree_failure",
    [
        ("linux", None),
        ("win32", None),
        ("win32", "missing"),
        ("win32", "timeout"),
        ("win32", "exit"),
        ("linux", "unreaped"),
    ],
)
def test_ocr_timeout_is_bounded_and_private_temp_files_are_removed(
    tmp_path, monkeypatch, platform, tree_failure
):
    dependency_root = tmp_path / "trusted-site"
    specs = {
        module: importlib.util.spec_from_file_location(
            module, dependency_root / module / "__init__.py"
        )
        for module in ("rapidocr_onnxruntime", "pypdfium2")
    }
    monkeypatch.setattr(importlib.util, "find_spec", specs.get)
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "untrusted"))
    monkeypatch.setattr(
        local_ocr,
        "sys",
        SimpleNamespace(
            version_info=(3, 12), executable=local_ocr.sys.executable, platform=platform
        ),
    )
    monkeypatch.setenv("SYSTEMROOT", r"C:\Windows")
    for key in (
        "EVIDENCEFORGE_MODEL_API_KEY",
        "evidenceforge_model_api_key",
        "LANGSMITH_API_KEY",
        "OPENAI_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "PYTHONHOME",
    ):
        monkeypatch.setenv(key, "private-fixture-value")

    calls = []

    class Worker:
        pid = 123456
        returncode = None

        def wait(self, timeout):
            calls.append(("wait", timeout))
            if self.returncode is None or tree_failure == "unreaped":
                raise subprocess.TimeoutExpired("local_ocr", timeout)
            return self.returncode

        def poll(self):
            return self.returncode

        def kill(self):
            calls.append(("kill",))
            self.returncode = -9

    worker = Worker()

    def popen(command, **kwargs):
        assert command[:3] == [
            local_ocr.sys.executable,
            "-m",
            "evidenceforge.storage.ocr_worker",
        ]
        assert "shell" not in kwargs
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert kwargs["stdout"] is subprocess.DEVNULL
        assert kwargs["stderr"] is subprocess.DEVNULL
        environment = kwargs["env"]
        assert not any("KEY" in key.upper() for key in environment)
        assert "PYTHONHOME" not in environment
        assert environment["PYTHONPATH"].split(os.pathsep) == [
            str(Path(local_ocr.__file__).resolve().parents[2]),
            str(dependency_root.resolve()),
        ]
        return worker

    def taskkill(command, **kwargs):
        calls.append(("tree",))
        assert platform == "win32"
        assert Path(command[0]) == Path(r"C:\Windows") / "System32" / "taskkill.exe"
        assert command[1:] == ["/PID", str(worker.pid), "/T", "/F"]
        assert "shell" not in kwargs
        assert kwargs["timeout"] == 5
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert kwargs["stdout"] is subprocess.DEVNULL
        assert kwargs["stderr"] is subprocess.DEVNULL
        assert not any("KEY" in key.upper() for key in kwargs["env"])
        if tree_failure == "missing":
            raise FileNotFoundError("private-native-detail")
        if tree_failure == "timeout":
            raise subprocess.TimeoutExpired(command, 5)
        if tree_failure == "exit":
            return SimpleNamespace(returncode=1)
        worker.returncode = -1
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(subprocess, "run", taskkill)
    with pytest.raises(LocalOcrFailure, match="time limit") as caught:
        transcribe_pdf(b"fixture", (1,), OcrLimits(timeout_seconds=1), tmp_path)
    assert "private" not in str(caught.value)
    assert ("cleanup could not be confirmed" in str(caught.value)) == (tree_failure is not None)
    expected = (
        [("wait", 1), ("tree",), ("wait", 5)]
        if platform == "win32" and tree_failure is None
        else [("wait", 1), *([("tree",)] if platform == "win32" else []), ("kill",), ("wait", 5)]
    )
    assert calls == expected
    assert not list(tmp_path.glob(".ocr-*"))


def test_ocr_actual_image_only_pdf_is_transcribed_locally(tmp_path):
    pytest.importorskip("rapidocr_onnxruntime")
    pytest.importorskip("pypdfium2")
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1200, 500), "white")
    draw = ImageDraw.Draw(image)
    draw.text(
        (50, 70), "Solar generation is 123 GWh.", font=ImageFont.load_default(size=44), fill="black"
    )
    path = tmp_path / "actual-scan.pdf"
    image.save(path, "PDF", resolution=150)
    assert not (PdfReader(path).pages[0].extract_text() or "").strip()
    store = DocumentStore(tmp_path / "documents", DocumentOptions(enable_ocr=True))
    record = store.ingest(path)
    chunks = store.chunks("local", record.id)
    assert chunks, record.warnings
    transcript = " ".join(chunk.text for chunk in chunks)
    assert "Solar" in transcript and "123" in transcript and "GWh" in transcript
    assert all(chunk.page == 1 for chunk in chunks)
    assert record.status == "partial"
    assert any("verify" in warning and "OCR transcript" in warning for warning in record.warnings)


@pytest.mark.parametrize("enable_ocr", [False, True])
def test_ocr_report_discloses_transcript_in_markdown_and_json(tmp_path, monkeypatch, enable_ocr):
    path = tmp_path / "scan.pdf"
    blank_pdf(path)
    monkeypatch.setattr(
        "evidenceforge.storage.documents.transcribe_pdf",
        lambda *_: {
            1: "Synthetic solar electricity output depends on sunlight.",
            2: "Synthetic wind electricity output depends on wind speed.",
        },
    )
    data_root = tmp_path / "data"
    store = DocumentStore(data_root / "documents", DocumentOptions(enable_ocr=enable_ocr))
    record = store.ingest(path)
    state = asyncio.run(
        ResearchService(data_root).run(
            ResearchRequest(
                question="Compare solar and wind electricity output.", document_ids=(record.id,)
            )
        )
    )
    markdown = render_report(state)
    exported = json.loads(report_export(state))
    if enable_ocr:
        assert state["run_status"] == "completed"
        assert OCR_TRANSCRIPT_LIMITATION in markdown
        assert OCR_TRANSCRIPT_LIMITATION in exported["limitations"]
        transcripts = exported["ocr_transcripts"]
        assert transcripts
        assert {item["document_id"] for item in transcripts} == {record.id}
        assert {item["page"] for item in transcripts} == {1, 2}
        assert all(item["section"] == "local OCR transcription" for item in transcripts)
    else:
        # Selected textless documents cannot provide a usable query adapter.
        assert state["run_status"] == "failed"
        assert state["stop_reason"] == "fatal_error"
        assert not state["evidence_store"] and not state["report_claims"]
        assert state["tool_errors"]
        assert OCR_TRANSCRIPT_LIMITATION not in markdown
        assert OCR_TRANSCRIPT_LIMITATION not in exported["limitations"]
        assert exported["ocr_transcripts"] == []
