"""Cloud bootstrap and UI gates never make live calls during verification."""

import json
from pathlib import Path

import pytest

from evidenceforge.auth import password_hash
from evidenceforge.cloud import configure_cloud
from evidenceforge.config import ConfigurationError, Settings


def test_live_cloud_removes_previous_login_and_retains_private_keys():
    env = {"EVIDENCEFORGE_AUTH_REQUIRED": "true"}
    secrets = {
        "EVIDENCEFORGE_MODEL_API_KEY": "synthetic-gemini-key",
        "EVIDENCEFORGE_TAVILY_API_KEY": "synthetic-tavily-key",
        "EVIDENCEFORGE_MODEL_ID": "synthetic-model",
    }
    assert configure_cloud(env, secrets) is False
    assert env["EVIDENCEFORGE_AUTH_REQUIRED"] == "false"
    assert env["EVIDENCEFORGE_MODEL_API_KEY"] == "synthetic-gemini-key"
    assert env["EVIDENCEFORGE_TAVILY_API_KEY"] == "synthetic-tavily-key"
    budget = json.loads(env["EVIDENCEFORGE_BUDGET"])
    assert budget["max_model_calls"] == 6 and budget["max_searches"] == 1
    assert budget["max_attempts_per_call"] == 1
    assert budget["max_rewrites"] == 1
    assert env["LANGSMITH_TRACING"] == "false"


def test_demo_is_explicit_and_removes_provider_keys():
    env = {
        "EVIDENCEFORGE_MODEL_API_KEY": "synthetic-key",
        "EVIDENCEFORGE_TAVILY_API_KEY": "synthetic-key",
    }
    assert configure_cloud(env, {"EVIDENCEFORGE_CLOUD_MODE": "demo"}) is True
    assert env["EVIDENCEFORGE_MODEL_PROVIDER"] == "fixture"
    assert env["EVIDENCEFORGE_MODEL_API_KEY"] == ""
    assert env["EVIDENCEFORGE_TAVILY_API_KEY"] == ""


def test_cloud_accepts_nested_secret_budget_for_public_access():
    env = {}
    assert configure_cloud(env, {"EVIDENCEFORGE_BUDGET": {"max_model_calls": 8}}) is False
    assert json.loads(env["EVIDENCEFORGE_BUDGET"]) == {"max_model_calls": 8}
    assert env["EVIDENCEFORGE_AUTH_REQUIRED"] == "false"


def test_invalid_cloud_mode_is_redacted():
    with pytest.raises(ConfigurationError, match="Cloud mode must be live or demo"):
        configure_cloud({}, {"EVIDENCEFORGE_CLOUD_MODE": "synthetic-secret-value"})


def test_hosted_live_entrypoint_requires_login_before_controls(monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    for key, value in {
        "CLOUD_MODE": "live",
        "CLOUD_ACCESS": "login",
        "MODEL_PROVIDER": "gemini",
        "MODEL_ID": "synthetic-model",
        "MODEL_API_KEY": "synthetic-key",
        "TAVILY_API_KEY": "synthetic-key",
        "AUTH_REQUIRED": "false",
        "AUTH_PASSWORD_HASH": password_hash("synthetic-password-for-testing"),
    }.items():
        monkeypatch.setenv("EVIDENCEFORGE_" + key, value)
    at = AppTest.from_file(
        Path(__file__).parents[1] / "scripts/streamlit_cloud/streamlit_app.py",
        default_timeout=90,
    ).run()
    assert not at.exception and not at.error
    assert any(h.value == "Sign in to EvidenceForge" for h in at.subheader)
    assert not any(b.label == "Create plan" for b in at.button)
    assert not at.get("file_uploader")
    assert not at.selectbox
    next(t for t in at.text_input if t.label == "Username").set_value("admin")
    next(t for t in at.text_input if t.label == "Password").set_value(
        "synthetic-password-for-testing"
    )
    next(b for b in at.button if b.label == "Sign in").click().run()
    assert not at.exception and not at.error
    assert next(s for s in at.selectbox if s.label == "Reasoning provider").value == (
        "Gemini (configured)"
    )
    assert next(c for c in at.checkbox if c.label == "Search live web with Tavily").value
    assert at.session_state["current_owner"] == "hosted"
    assert not any(t.label == "Local workspace scope" for t in at.text_input)
    assert "active_job" not in at.session_state


def test_configured_workbench_selects_live_controls_without_calls(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    from evidenceforge import ui

    settings = Settings(
        model_provider="gemini",
        model_id="synthetic-model",
        model_api_key="synthetic-key",
        tavily_api_key="synthetic-key",
        data_dir=tmp_path,
    )
    monkeypatch.setattr(ui, "load_settings", lambda: settings)
    monkeypatch.setattr(ui, "gettempdir", lambda: str(tmp_path))
    at = AppTest.from_string(
        "from evidenceforge.ui import main\nmain(cloud_hosted=True)",
        default_timeout=90,
    ).run()
    assert not at.exception and not at.error
    assert next(s for s in at.selectbox if s.label == "Reasoning provider").value == (
        "Gemini (configured)"
    )
    assert next(c for c in at.checkbox if c.label == "Search live web with Tavily").value
    assert any("temporary" in w.value for w in at.warning)
    assert "active_job" not in at.session_state


def test_missing_hosted_configuration_shows_safe_setup_error(monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("EVIDENCEFORGE_CLOUD_MODE", "live")
    monkeypatch.setenv("EVIDENCEFORGE_MODEL_PROVIDER", "fixture")
    monkeypatch.setenv("EVIDENCEFORGE_AUTH_PASSWORD_HASH", "")
    at = AppTest.from_file(
        Path(__file__).parents[1] / "scripts/streamlit_cloud/streamlit_app.py",
        default_timeout=90,
    ).run()
    assert not at.exception
    assert len(at.error) == 1
    assert "Live hosted setup is incomplete" in at.error[0].value
    assert not any(b.label == "Create plan" for b in at.button)


def test_login_remains_available_when_explicitly_selected():
    env = {}
    assert configure_cloud(env, {"EVIDENCEFORGE_CLOUD_ACCESS": "login"}) is False
    assert env["EVIDENCEFORGE_AUTH_REQUIRED"] == "true"


def test_public_hosted_visitors_cannot_choose_or_share_scopes(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    from evidenceforge import ui

    settings = Settings(
        model_provider="gemini",
        model_id="synthetic-model",
        model_api_key="synthetic-key",
        tavily_api_key="synthetic-key",
        data_dir=tmp_path,
    )
    monkeypatch.setattr(ui, "load_settings", lambda: settings)
    monkeypatch.setattr(ui, "gettempdir", lambda: str(tmp_path))
    source = "from evidenceforge.ui import main\nmain(cloud_hosted=True)"
    first = AppTest.from_string(source, default_timeout=90).run()
    second = AppTest.from_string(source, default_timeout=90).run()
    assert not first.exception and not second.exception
    assert first.session_state["current_owner"] != second.session_state["current_owner"]
    assert first.session_state["current_owner"] not in {"hosted", "local"}
    assert not first.text_input and not second.text_input
    assert not any(b.label == "Sign in" for b in first.button)
    assert any(b.label == "Create plan" for b in first.button)
