"""Streamlit Cloud bootstrap with explicit offline mode and optional live login."""

import json
from collections.abc import Mapping, MutableMapping

from evidenceforge.config import ConfigurationError

DEFAULT_CLOUD_MODEL = "gemini-3.1-flash-lite"

CLOUD_KEYS = (
    "EVIDENCEFORGE_CLOUD_MODE",
    "EVIDENCEFORGE_CLOUD_ACCESS",
    "EVIDENCEFORGE_MODEL_PROVIDER",
    "EVIDENCEFORGE_MODEL_ID",
    "EVIDENCEFORGE_MODEL_API_KEY",
    "EVIDENCEFORGE_TAVILY_API_KEY",
    "EVIDENCEFORGE_AUTH_USERNAME",
    "EVIDENCEFORGE_AUTH_PASSWORD_HASH",
    "EVIDENCEFORGE_BUDGET",
)


def configure_cloud(environ: MutableMapping[str, str], secrets: Mapping[str, object]) -> bool:
    """Return fixture mode; public live access is the default, login is opt-in."""
    # Linux permits both uppercase and lowercase env names; Pydantic folds them.
    # A stale lowercase blank can otherwise shadow a valid canonical secret.
    normalized: dict[str, object] = {}
    for name, value in secrets.items():
        canonical = name.upper()
        if canonical not in normalized or name == canonical:
            normalized[canonical] = value
    secrets = normalized
    for name in tuple(environ):
        canonical = name.upper()
        if name != canonical and (
            canonical.startswith("EVIDENCEFORGE_")
            or canonical
            in {
                "GEMINI_API_KEY",
                "GOOGLE_API_KEY",
                "TAVILY_API_KEY",
                "GEMINI_MODEL",
                "GEMINI_MODEL_ID",
                "LANGSMITH_TRACING",
            }
        ):
            if not environ.get(canonical, "").strip():
                environ[canonical] = environ[name]
            del environ[name]
    for key in CLOUD_KEYS:
        if key in secrets:
            value = secrets[key]
            environ[key] = json.dumps(value) if isinstance(value, Mapping) else str(value)
    mode = environ.get("EVIDENCEFORGE_CLOUD_MODE", "live").strip().lower()
    if mode not in {"live", "demo"}:
        raise ConfigurationError("Cloud mode must be live or demo.")
    environ["EVIDENCEFORGE_TRACING_ENABLED"] = "false"
    environ["EVIDENCEFORGE_TRACE_PAYLOADS"] = "false"
    environ["LANGSMITH_TRACING"] = "false"
    if mode == "demo":
        environ["EVIDENCEFORGE_MODEL_PROVIDER"] = "fixture"
        for key in ("MODEL_API_KEY", "MODEL_ID", "TAVILY_API_KEY"):
            environ["EVIDENCEFORGE_" + key] = ""
        return True
    access = environ.get("EVIDENCEFORGE_CLOUD_ACCESS", "public").strip().lower()
    if access not in {"public", "login"}:
        raise ConfigurationError("Cloud access must be public or login.")
    environ["EVIDENCEFORGE_AUTH_REQUIRED"] = str(access == "login").lower()
    # Live Cloud uses Gemini. A prior demo rerun may have left fixture/blank env values.
    environ["EVIDENCEFORGE_MODEL_PROVIDER"] = "gemini"
    for canonical, aliases in {
        "EVIDENCEFORGE_MODEL_API_KEY": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "EVIDENCEFORGE_TAVILY_API_KEY": ("TAVILY_API_KEY",),
        "EVIDENCEFORGE_MODEL_ID": ("GEMINI_MODEL", "GEMINI_MODEL_ID"),
    }.items():
        supplied = [
            secrets.get(canonical),
            *(secrets.get(alias) for alias in aliases),
            environ.get(canonical),
            *(environ.get(alias) for alias in aliases),
        ]
        value = next(
            (item.strip() for item in supplied if isinstance(item, str) and item.strip()),
            "",
        )
        environ[canonical] = value
    if not environ["EVIDENCEFORGE_MODEL_ID"]:
        environ["EVIDENCEFORGE_MODEL_ID"] = DEFAULT_CLOUD_MODEL
    environ.setdefault(
        "EVIDENCEFORGE_BUDGET",
        json.dumps(
            {
                "max_model_calls": 6,
                "max_subquestions": 1,
                "max_queries_per_pass": 1,
                "max_searches": 1,
                "max_research_passes": 1,
                "max_rewrites": 1,
                "reserved_quality_calls": 3,
                "max_total_tokens": 100000,
                "max_elapsed_seconds": 1800,
                "max_concurrency": 1,
                "max_attempts_per_call": 1,
            }
        ),
    )
    return False


def validate_cloud_configuration(environ: Mapping[str, str]) -> None:
    """Report only missing field names before Pydantic's root model validator runs."""
    if environ.get("EVIDENCEFORGE_CLOUD_MODE", "live").strip().lower() == "demo":
        return
    missing = [
        key
        for key in (
            "EVIDENCEFORGE_MODEL_ID",
            "EVIDENCEFORGE_MODEL_API_KEY",
            "EVIDENCEFORGE_TAVILY_API_KEY",
        )
        if not environ.get(key, "").strip()
    ]
    if (
        environ.get("EVIDENCEFORGE_AUTH_REQUIRED") == "true"
        and not environ.get("EVIDENCEFORGE_AUTH_PASSWORD_HASH", "").strip()
    ):
        missing.append("EVIDENCEFORGE_AUTH_PASSWORD_HASH")
    if missing:
        raise ConfigurationError(
            "Live hosted setup is incomplete. Missing: "
            + ", ".join(missing)
            + ". Add these in Streamlit App settings > Secrets and save."
        )
