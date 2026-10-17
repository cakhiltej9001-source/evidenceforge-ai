"""Optional UI executes real service controls and presents scoped outputs."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

from evidenceforge.storage.documents import DocumentStore
from evidenceforge.ui import ingest_upload
from evidenceforge.workbench import LocalWorkbench


def test_ui_create_approve_download_and_change_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCEFORGE_DATA_DIR", str(tmp_path))
    original = LocalWorkbench.submit
    apps = []

    def completed_submit(self, owner, key, operation):
        # Real background service, awaited here to keep UI assertions deterministic.
        apps.append(self)
        result = original(self, owner, key, operation)
        self.jobs[(owner, key)].result(timeout=90)
        return result

    monkeypatch.setattr(LocalWorkbench, "submit", completed_submit)
    at = AppTest.from_file(
        Path(__file__).parents[1] / "src/evidenceforge/ui.py", default_timeout=90
    )
    try:
        at.run()
        assert not at.exception and not at.error
        next(r for r in at.radio if r.label == "Research mode").set_value(
            "Synthetic demonstration"
        ).run()
        next(t for t in at.text_area if t.label == "Research question").set_value(
            "Compare solar and wind electricity output."
        )
        next(b for b in at.button if b.label == "Create plan").click().run()
        assert not at.exception and not at.error
        assert any(h.value == "Review the research plan" for h in at.subheader)
        next(b for b in at.button if b.label == "Save edited plan").click().run()
        at.run()
        assert not at.exception and not at.error
        assert any("Plan version: 2" in c.value for c in at.caption)
        assert {e.label for e in at.expander} >= {
            "Live timeline",
            "Coverage and unresolved questions",
            "Budget and usage",
        }
        next(b for b in at.button if b.label == "Approve plan").click().run()
        at.run()
        assert not at.exception and not at.error
        assert {b.label for b in at.get("download_button")} >= {
            "Download Markdown",
            "Download JSON",
        }
        assert any(h.value == "Inspect a finding" for h in at.subheader)
        next(t for t in at.text_input if t.label == "Local workspace scope").set_value(
            "other"
        ).run()
        assert not at.exception
        assert not at.get("download_button")
        assert "selected_thread" not in at.session_state
    finally:
        for app in apps:
            app.close()


def test_upload_is_scoped_and_does_not_use_client_path(tmp_path):
    store = DocumentStore(tmp_path / "documents")
    record = ingest_upload(
        store, "alice", "../../outside.txt", b"Solar electricity depends on sunlight."
    )
    assert store.get("alice", record.id).id == record.id
    assert not (tmp_path / "outside.txt").exists()
    assert not list((store.root / "uploads").iterdir())
    with pytest.raises(ValueError):
        ingest_upload(store, "alice", "run.exe", b"Not a document")
