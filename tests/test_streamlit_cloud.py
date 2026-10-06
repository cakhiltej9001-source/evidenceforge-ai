"""The public demo completes a real run without exposing it to another visitor."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

from evidenceforge import ui
from evidenceforge.storage.checkpoints import CheckpointFailure
from evidenceforge.workbench import LocalWorkbench


def test_public_demo_completes_and_isolates_visitors(tmp_path, monkeypatch):
    monkeypatch.setenv("EVIDENCEFORGE_AUTH_REQUIRED", "false")
    monkeypatch.delenv("RENDER", raising=False)
    for key, value in {
        "MODEL_PROVIDER": "fixture",
        "MODEL_API_KEY": "",
        "MODEL_ID": "",
        "TAVILY_API_KEY": "",
        "TRACING_ENABLED": "false",
    }.items():
        monkeypatch.setenv("EVIDENCEFORGE_" + key, value)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setattr(ui, "gettempdir", lambda: str(tmp_path))
    original = LocalWorkbench.submit
    apps = []

    def completed_submit(self, owner, key, operation):
        apps.append(self)
        result = original(self, owner, key, operation)
        self.jobs[(owner, key)].result(timeout=90)
        return result

    monkeypatch.setattr(LocalWorkbench, "submit", completed_submit)
    entrypoint = Path(__file__).parents[1] / "scripts/streamlit_cloud/streamlit_app.py"
    first = AppTest.from_file(entrypoint, default_timeout=90)
    second = AppTest.from_file(entrypoint, default_timeout=90)
    try:
        first.run()
        second.run()
        assert not first.exception and not first.error
        assert not second.exception and not second.error
        assert not first.get("file_uploader")
        assert not first.text_input and not first.checkbox
        reasoning = next(s for s in first.selectbox if s.label == "Reasoning provider")
        assert reasoning.options == ["Offline"]
        first_owner = first.session_state["public_demo_owner"]
        second_owner = second.session_state["public_demo_owner"]
        assert first_owner != second_owner
        next(b for b in first.button if b.label == "Create plan").click().run()
        next(b for b in first.button if b.label == "Approve plan").click().run()
        first.run()
        assert not first.exception and not first.error
        assert {b.label for b in first.get("download_button")} == {
            "Download Markdown",
            "Download JSON",
        }
        thread = first.session_state["selected_thread"]
        app = apps[0]
        assert app.snapshot(first_owner, thread)["run_status"] == "completed"
        assert app.threads(second_owner) == []
        with pytest.raises(CheckpointFailure):
            app.snapshot(second_owner, thread)
        second.run()
        assert not second.get("download_button")
        assert not any(s.label == "Saved thread" for s in second.selectbox)
    finally:
        for app in apps:
            app.close()
