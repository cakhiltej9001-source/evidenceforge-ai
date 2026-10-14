"""Regression checks for cloud model defaults, key aliases and safe missing-field errors."""

import json
from pathlib import Path

import pytest

from evidenceforge.cloud import (
    DEFAULT_CLOUD_MODEL,
    configure_cloud,
    validate_cloud_configuration,
)
from evidenceforge.config import ConfigurationError, Settings


def configured(env):
    return Settings(
        _env_file=None,
        model_provider=env["EVIDENCEFORGE_MODEL_PROVIDER"],
        model_id=env["EVIDENCEFORGE_MODEL_ID"],
        model_api_key=env["EVIDENCEFORGE_MODEL_API_KEY"],
        tavily_api_key=env["EVIDENCEFORGE_TAVILY_API_KEY"],
        budget=json.loads(env["EVIDENCEFORGE_BUDGET"]),
    )


def test_missing_model_id_uses_verified_default_with_existing_keys():
    env = {"EVIDENCEFORGE_MODEL_PROVIDER": "fixture", "EVIDENCEFORGE_MODEL_ID": ""}
    configure_cloud(
        env,
        {
            "EVIDENCEFORGE_MODEL_API_KEY": "synthetic-gemini",
            "EVIDENCEFORGE_TAVILY_API_KEY": "synthetic-tavily",
        },
    )
    validate_cloud_configuration(env)
    settings = configured(env)
    assert settings.model_provider == "gemini"
    assert settings.model_id == DEFAULT_CLOUD_MODEL


@pytest.mark.parametrize("key_name", ["GEMINI_API_KEY", "GOOGLE_API_KEY"])
def test_standard_key_names_load_without_credential_echo(key_name):
    env = {}
    configure_cloud(
        env, {key_name: "synthetic-private-gemini", "TAVILY_API_KEY": "synthetic-private-tavily"}
    )
    validate_cloud_configuration(env)
    settings = configured(env)
    assert settings.model_api_key.get_secret_value() == "synthetic-private-gemini"
    assert settings.tavily_api_key.get_secret_value() == "synthetic-private-tavily"
    assert "synthetic-private" not in settings.model_dump_json()


def test_explicit_canonical_secret_wins_over_alias_and_environment():
    env = {"GEMINI_API_KEY": "synthetic-env"}
    configure_cloud(
        env,
        {
            "EVIDENCEFORGE_MODEL_API_KEY": "synthetic-canonical",
            "GEMINI_API_KEY": "synthetic-alias",
            "EVIDENCEFORGE_MODEL_ID": "synthetic-chosen-model",
        },
    )
    assert env["EVIDENCEFORGE_MODEL_API_KEY"] == "synthetic-canonical"
    assert env["EVIDENCEFORGE_MODEL_ID"] == "synthetic-chosen-model"


def test_blank_stale_fields_can_use_standard_environment_aliases():
    env = {
        "EVIDENCEFORGE_MODEL_API_KEY": "",
        "EVIDENCEFORGE_MODEL_ID": "",
        "GEMINI_API_KEY": "synthetic-gemini",
        "TAVILY_API_KEY": "synthetic-tavily",
    }
    configure_cloud(env, {})
    validate_cloud_configuration(env)
    assert configured(env).model_api_key is not None


def test_missing_keys_are_named_without_echoing_other_values():
    env = {}
    configure_cloud(env, {"EVIDENCEFORGE_MODEL_ID": "synthetic-sensitive-model-name"})
    with pytest.raises(ConfigurationError) as error:
        validate_cloud_configuration(env)
    text = str(error.value)
    assert "EVIDENCEFORGE_MODEL_API_KEY" in text
    assert "EVIDENCEFORGE_TAVILY_API_KEY" in text
    assert "synthetic-sensitive-model-name" not in text
    assert "EVIDENCEFORGE_MODEL_ID," not in text


def test_demo_never_requires_provider_configuration():
    env = {}
    configure_cloud(env, {"EVIDENCEFORGE_CLOUD_MODE": "demo"})
    validate_cloud_configuration(env)
    assert env["EVIDENCEFORGE_MODEL_API_KEY"] == ""


def test_missing_key_entrypoint_shows_cloud_action_instead_of_root_error(monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("EVIDENCEFORGE_CLOUD_MODE", "live")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    at = AppTest.from_file(
        Path(__file__).parents[1] / "scripts/streamlit_cloud/streamlit_app.py",
        default_timeout=90,
    ).run()
    assert not at.exception
    assert len(at.error) == 1
    assert "EVIDENCEFORGE_MODEL_API_KEY" in at.error[0].value
    assert "Streamlit App settings > Secrets" in at.error[0].value
    assert "model configuration" not in at.error[0].value
    assert not any(b.label == "Create plan" for b in at.button)
