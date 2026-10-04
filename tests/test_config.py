import pytest

from evidenceforge.config import ConfigurationError, load_settings


def test_fixture_defaults_need_no_credentials_or_directory_creation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = load_settings(env_file=None)
    assert settings.model_provider == "fixture"
    assert not settings.tracing_enabled
    assert settings.model_api_key is None
    assert not settings.data_dir.exists()


def test_environment_overrides_dotenv_and_parses_nested_limits(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text(
        "EVIDENCEFORGE_MODEL_PROVIDER=fixture\n"
        "EVIDENCEFORGE_BUDGET__MAX_SEARCHES=8\n"
        "EVIDENCEFORGE_MODEL_ID=\n"
        "EVIDENCEFORGE_MODEL_API_KEY=\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EVIDENCEFORGE_BUDGET__MAX_SEARCHES", "6")
    settings = load_settings(path)
    assert settings.budget.max_searches == 6
    assert settings.model_id is None
    assert settings.model_api_key is None


def test_live_settings_require_explicit_model_and_key(monkeypatch):
    monkeypatch.setenv("EVIDENCEFORGE_MODEL_PROVIDER", "openai")
    with pytest.raises(ConfigurationError, match="model configuration"):
        load_settings(None)


def test_secrets_excluded_from_public_dict_json_and_repr(monkeypatch):
    monkeypatch.setenv("EVIDENCEFORGE_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("EVIDENCEFORGE_MODEL_ID", "user-configured-model")
    monkeypatch.setenv("EVIDENCEFORGE_MODEL_API_KEY", "synthetic-private-model-key")
    monkeypatch.setenv("EVIDENCEFORGE_TAVILY_API_KEY", "synthetic-private-search-key")
    settings = load_settings(None)
    for output in (repr(settings), str(settings.model_dump()), settings.model_dump_json()):
        assert "synthetic-private" not in output
    assert "model_api_key" not in settings.model_dump()
    assert "tavily_api_key" not in settings.model_dump()


@pytest.mark.parametrize("value", ["0", "true", "not_a_number"])
def test_invalid_environment_limits_fail_helpfully_without_values(monkeypatch, value):
    monkeypatch.setenv("EVIDENCEFORGE_BUDGET__MAX_SEARCHES", value)
    with pytest.raises(ConfigurationError, match="Invalid settings"):
        load_settings(None)


def test_diagnostic_errors_do_not_echo_supplied_secret(monkeypatch):
    marker = "synthetic-sensitive-invalid-value"
    monkeypatch.setenv("EVIDENCEFORGE_MODEL_PROVIDER", marker)
    with pytest.raises(ConfigurationError) as failure:
        load_settings(None)
    assert marker not in str(failure.value)


def test_sample_environment_file_loads_without_live_keys():
    settings = load_settings(".env.example")
    assert settings.model_provider == "fixture"
    assert settings.model_api_key is None
    assert settings.tavily_api_key is None
