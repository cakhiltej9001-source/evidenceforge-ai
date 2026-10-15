"""Real research never silently spends provider calls on synthetic fixtures."""

from types import SimpleNamespace

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

from evidenceforge import ui
from evidenceforge.config import Settings
from evidenceforge.storage.documents import DocumentStore


def form(tmp_path, monkeypatch):
    settings = Settings(
        model_provider="gemini",
        model_id="synthetic-model",
        model_api_key="synthetic-key",
        tavily_api_key="synthetic-key",
        data_dir=tmp_path,
    )
    starts = []

    def start(request, demo, **options):
        starts.append((request, demo, options))
        return None

    app = SimpleNamespace(
        data_dir=tmp_path,
        active=lambda owner: False,
        threads=lambda owner: [],
        start=start,
    )
    monkeypatch.setattr(ui, "load_settings", lambda: settings)
    monkeypatch.setattr(ui, "workbench", lambda directory: app)
    return AppTest.from_string(
        "from evidenceforge.ui import main\nmain()", default_timeout=90
    ).run(), starts


@pytest.mark.parametrize("provider", ["Offline", "Gemini (configured)"])
def test_source_free_research_is_blocked_before_workbench_start(tmp_path, monkeypatch, provider):
    at, starts = form(tmp_path, monkeypatch)
    assert not at.exception
    assert next(r for r in at.radio if r.label == "Research mode").value == (
        "Research with real sources"
    )
    assert not any(s.label == "Synthetic scenario" for s in at.selectbox)
    next(t for t in at.text_area if t.label == "Research question").set_value(
        "What is the capital of Telangana?"
    )
    next(s for s in at.selectbox if s.label == "Reasoning provider").set_value(provider)
    next(c for c in at.checkbox if c.label == "Search live web with Tavily").uncheck()
    next(b for b in at.button if b.label == "Create plan").click().run()
    assert not at.exception
    assert starts == []
    assert any("No research sources selected" in e.value for e in at.error)
    assert any("No API calls were made" in e.value for e in at.error)
    assert "active_job" not in at.session_state


@pytest.mark.parametrize("source", ["web", "document"])
def test_explicit_real_sources_reach_the_workbench(tmp_path, monkeypatch, source):
    at, starts = form(tmp_path, monkeypatch)
    document_ids = ()
    if source == "document":
        path = tmp_path / "capital.txt"
        path.write_text("Synthetic test text for the source selection regression.")
        record = DocumentStore(tmp_path / "documents").ingest(path, "local")
        document_ids = (record.id,)
        next(t for t in at.text_area if t.label.startswith("Existing document IDs")).set_value(
            record.id
        )
        next(c for c in at.checkbox if c.label == "Search live web with Tavily").uncheck()
    next(b for b in at.button if b.label == "Create plan").click().run()
    assert not at.exception and not at.error
    assert len(starts) == 1
    request, _, options = starts[0]
    assert request.document_ids == document_ids
    assert options["gemini"] is True
    assert options["live_web"] is (source == "web")
    assert options["live_energy"] is False
