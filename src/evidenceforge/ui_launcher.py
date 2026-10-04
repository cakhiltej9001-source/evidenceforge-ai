"""Launch Streamlit locally, with explicit container binding and port controls."""

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the EvidenceForge workbench.")
    parser.add_argument("--host", choices=("127.0.0.1", "0.0.0.0"), default="127.0.0.1")
    parser.add_argument("--port", type=int, default=os.environ.get("PORT", "8501"))
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535.")
    if importlib.util.find_spec("streamlit") is None:
        print("Install UI dependencies: uv sync --locked --extra ui")
        return 1
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(Path(__file__).with_name("ui.py")),
            f"--server.address={args.host}",
            f"--server.port={args.port}",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
            "--server.maxUploadSize=4",
            "--server.enableXsrfProtection=true",
        ],
    )


if __name__ == "__main__":
    raise SystemExit(main())
