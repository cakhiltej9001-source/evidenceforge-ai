"""Blocked external sites never prevent reading the report's retained evidence."""

import asyncio
from copy import deepcopy
from pathlib import Path

import pytest

from evidenceforge.graph.state import StateSnapshot
from evidenceforge.models.research import FixtureResearchModel
from evidenceforge.reporting import render_report, retained_source_passages, retained_source_text
from evidenceforge.retrieval.contracts import RetrievalBatch, RetrievedSource
from evidenceforge.retrieval.fixtures import FixtureRetrievalAdapter
from evidenceforge.schemas import ResearchRequest, SourceType
from evidenceforge.services.research import ResearchService
from evidenceforge.services.retrieval import RetrievalService


@pytest.fixture
def source_report(tmp_path):
    # Only synthetic text is stored; this URL is never requested by the fixture adapter.
    batch = RetrievalBatch(
        results=(
            RetrievedSource(
                title="Synthetic source [literal] <b>title</b>",
                url="https://www.globalelectricity.org/solar-vs-wind-energy/",
                content="Synthetic solar electricity depends on sunlight: café <b>literal</b>.",
            ),
        )
    )
    service = ResearchService(
        tmp_path,
        model=FixtureResearchModel(
            plan_output={
                "questions": [
                    {
                        "question": "What does the solar source say?",
                        "acceptance_criteria": ["solar"],
                    }
                ]
            }
        ),
        retrieval=RetrievalService(tmp_path, {SourceType.WEB: FixtureRetrievalAdapter(batch)}),
    )
    state = asyncio.run(service.run(ResearchRequest(question="What does the solar source say?")))
    assert state["final_report"] and state["report_claims"]
    for source in state["source_records"].values():
        source["access_status"] = "excerpt_only"
    for acquisition in state["source_acquisitions"].values():
        acquisition["content_scope"] = "search_excerpt"
    return state


def test_in_app_links_open_saved_evidence_and_downloads_keep_original_urls(source_report):
    local = render_report(source_report, local_source_links=True)
    exported = render_report(source_report)
    url = "https://www.globalelectricity.org/solar-vs-wind-energy/"
    assert "](#saved-source-1)" in local
    assert f"[Original website]({url})" in local
    assert "Source titles open saved passages below" in local
    assert "](#saved-source-1)" not in exported
    assert f"]({url})" in exported
    assert "HTTP 403" in exported and "JSON download" in exported
    assert "<b>title</b>" not in local  # Untrusted titles remain escaped in Markdown.


def test_download_preserves_exact_cited_text_and_excludes_uncited_material(source_report):
    original = StateSnapshot.model_validate(source_report)
    sid = original.final_report.source_ids[0]
    expected = retained_source_passages(original, sid)
    extra = deepcopy(next(iter(source_report["evidence_store"].values())))
    extra["id"] = "uncited_extra"
    source_report["evidence_store"][extra["id"]] = extra
    snapshot = StateSnapshot.model_validate(source_report)
    assert retained_source_passages(snapshot, sid) == expected
    assert retained_source_passages(snapshot, "unknown_source") == ()
    assert retained_source_text(snapshot, "unknown_source").startswith("No cited passages")
    download = retained_source_text(snapshot, sid)
    for passage in expected:
        assert passage.passage in download
    assert "café <b>literal</b>" in download
    assert "search_excerpt" in download and "Retrieved:" in download
    assert "not a full-page mirror" in download
    assert "uncited_extra" not in download


def test_saved_passages_and_text_download_work_without_a_network_request(
    source_report, monkeypatch
):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest, app_test

    from evidenceforge import ui

    monkeypatch.setattr(ui, "_test_saved_state", source_report, raising=False)
    stores = []
    original_storage = app_test.MemoryMediaFileStorage

    def storage(endpoint):
        instance = original_storage(endpoint)
        stores.append(instance)
        return instance

    monkeypatch.setattr(app_test, "MemoryMediaFileStorage", storage)
    at = AppTest.from_string(
        "from evidenceforge import ui\nui.show_report(ui._test_saved_state)",
        default_timeout=90,
    ).run()
    assert not at.exception and not at.error
    pdf_button = next(b for b in at.get("download_button") if b.label == "Download report PDF")
    pdf = stores[-1].get_file(Path(pdf_button.proto.url).name)
    assert pdf.filename == "research-report.pdf" and pdf.content.startswith(b"%PDF")
    assert any(h.value == "Saved source passages" for h in at.subheader)
    assert any("full-page access is not verified" in i.value for i in at.info)
    expected = retained_source_passages(
        StateSnapshot.model_validate(source_report), source_report["final_report"]["source_ids"][0]
    )
    assert {c.value for c in at.code} == {e.passage for e in expected}
    button = next(b for b in at.get("download_button") if b.label == "Download saved passages [1]")
    assert button.proto.ignore_rerun
    downloaded = stores[-1].get_file(Path(button.proto.url).name)
    assert downloaded.filename == "source-1-passages.txt"
    text = downloaded.content.decode("utf-8")
    assert all(e.passage in text for e in expected)
    assert "search_excerpt" in text
