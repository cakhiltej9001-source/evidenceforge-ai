"""Public Community Cloud demonstration without private data or paid providers."""

import os
import sys
from pathlib import Path

# This entrypoint demonstrates fixtures without live keys or tracing payloads.
os.environ["EVIDENCEFORGE_MODEL_PROVIDER"] = "fixture"
os.environ["EVIDENCEFORGE_MODEL_API_KEY"] = ""
os.environ["EVIDENCEFORGE_MODEL_ID"] = ""
os.environ["EVIDENCEFORGE_TAVILY_API_KEY"] = ""
os.environ["EVIDENCEFORGE_TRACING_ENABLED"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from evidenceforge.ui import main  # noqa: E402

main(public_demo=True)
