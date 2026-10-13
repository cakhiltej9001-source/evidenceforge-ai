"""Streamlit Cloud bootstrap with explicit offline mode and private live login."""

import json
from collections.abc import Mapping, MutableMapping

from evidenceforge.config import ConfigurationError

CLOUD_KEYS = (
    "EVIDENCEFORGE_CLOUD_MODE",
    "EVIDENCEFORGE_MODEL_PROVIDER",
    "EVIDENCEFORGE_MODEL_ID",
    "EVIDENCEFORGE_MODEL_API_KEY",
    "EVIDENCEFORGE_TAVILY_API_KEY",
    "EVIDENCEFORGE_AUTH_USERNAME",
    "EVIDENCEFORGE_AUTH_PASSWORD_HASH",
    "EVIDENCEFORGE_BUDGET",
)


def configure_cloud(environ: MutableMapping[str, str], secrets: Mapping[str, object]) -> bool:
    """Return fixture mode; live mode always requires the existing owner login."""
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
    environ["EVIDENCEFORGE_AUTH_REQUIRED"] = "true"
    environ.setdefault("EVIDENCEFORGE_MODEL_PROVIDER", "gemini")
    environ.setdefault(
        "EVIDENCEFORGE_BUDGET",
        json.dumps(
            {
                "max_model_calls": 6,
                "max_subquestions": 1,
                "max_queries_per_pass": 1,
                "max_searches": 1,
                "max_research_passes": 1,
                "max_rewrites": 0,
                "reserved_quality_calls": 3,
                "max_total_tokens": 100000,
                "max_elapsed_seconds": 1800,
                "max_concurrency": 1,
                "max_attempts_per_call": 1,
            }
        ),
    )
    return False
