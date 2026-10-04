"""Explicit environment/dotenv loading with redacted public output."""

import json
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, SettingsError

from evidenceforge.schemas import BudgetLimits


class ConfigurationError(ValueError):
    """A setup error whose public message never includes supplied values."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EVIDENCEFORGE_",
        env_nested_delimiter="__",
        extra="forbid",
        hide_input_in_errors=True,
        validate_default=True,
    )

    model_provider: Literal["fixture", "gemini", "openai", "anthropic", "groq"] = "fixture"
    model_id: str | None = None
    model_api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    tavily_api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    data_dir: Path = Path(".evidenceforge")
    tracing_enabled: bool = False
    budget: BudgetLimits = Field(default_factory=BudgetLimits)

    @field_validator("model_id", "model_api_key", "tavily_api_key", mode="before")
    @classmethod
    def blank_is_unconfigured(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("budget", mode="before")
    @classmethod
    def parse_environment_budget(cls, value: object) -> object:
        if isinstance(value, dict):
            return {
                key: json.loads(item) if isinstance(item, str) else item
                for key, item in value.items()
            }
        return value

    @model_validator(mode="after")
    def configured_live_model(self) -> Self:
        if self.model_provider != "fixture":
            if (
                self.model_id is None
                or self.model_api_key is None
                or not self.model_api_key.get_secret_value().strip()
            ):
                raise ValueError("live model configuration requires model ID and model API key")
        return self


def load_settings(env_file: Path | None = Path(".env")) -> Settings:
    """Environment overrides explicit dotenv, then defaults; no provider calls or IO setup."""
    try:
        return Settings(_env_file=env_file)  # type: ignore[call-arg]  # BaseSettings runtime option.
    except ValidationError as exc:
        # Do not propagate error input values or the original exception to public diagnostics.
        fields = sorted({".".join(str(part) for part in item["loc"]) for item in exc.errors()})
        description = ", ".join(field or "model configuration" for field in fields)
        raise ConfigurationError(f"Invalid settings: {description}. Check .env.example.") from None
    except SettingsError:
        raise ConfigurationError("Invalid environment setting. Check .env.example.") from None


def main() -> int:
    """Validate configuration and print only non-secret settings."""
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        print(str(exc))
        return 1
    print(json.dumps(settings.model_dump(mode="json"), indent=2))
    return 0
