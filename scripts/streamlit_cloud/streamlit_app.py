"""Community Cloud workbench with owner login and private provider secrets."""

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from evidenceforge.cloud import configure_cloud  # noqa: E402
from evidenceforge.config import ConfigurationError, load_settings  # noqa: E402
from evidenceforge.ui import main  # noqa: E402

try:
    try:
        secrets = dict(st.secrets)
    except FileNotFoundError:
        secrets = {}
    public_demo = configure_cloud(os.environ, secrets)
    settings = load_settings(env_file=None)
    if not public_demo and (
        settings.model_provider != "gemini"
        or settings.model_api_key is None
        or settings.tavily_api_key is None
        or settings.auth_password_hash is None
    ):
        raise ConfigurationError(
            "Live hosted setup is incomplete. The owner must add Gemini, Tavily "
            "and login settings in Streamlit App settings > Secrets."
        )
except ConfigurationError as exc:
    st.set_page_config(page_title="EvidenceForge", page_icon=":mag:", layout="wide")
    st.title("EvidenceForge live research")
    st.error(str(exc))
    st.stop()

main(public_demo=public_demo, cloud_hosted=not public_demo)
