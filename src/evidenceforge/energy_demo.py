"""Explicit energy-source acquisition with retained evidence and no model API calls."""

import argparse
import asyncio
import json
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from evidenceforge.config import ConfigurationError, load_settings
from evidenceforge.graph.state import ResearchState
from evidenceforge.retrieval.carbon_intensity import CarbonIntensityAdapter, CarbonIntensityFixture
from evidenceforge.retrieval.contracts import ArtifactFailure, RetrievalAdapter
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.research import atomic_write
from evidenceforge.services.retrieval import RetrievalService

QUESTION = "Compare solar and wind electricity generation shares in Great Britain."


async def execute(
    directory: Path, *, live: bool = False, adapter: RetrievalAdapter | None = None
) -> ResearchState:
    source = adapter or (CarbonIntensityAdapter() if live else CarbonIntensityFixture())
    try:
        return await RetrievalService(directory, {SourceType.WEB: source}).run(
            ResearchRequest(question=QUESTION),
            BudgetLimits(
                max_subquestions=1,
                max_queries_per_pass=1,
                max_searches=1,
                max_research_passes=1,
                max_attempts_per_call=1,
            ),
        )
    finally:
        if adapter is None and isinstance(source, CarbonIntensityAdapter):
            await source.aclose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire GB generation mix; no Gemini calls.")
    parser.add_argument("--live", action="store_true", help="Make one public NESO GET request.")
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args()
    try:
        directory = args.data_dir or load_settings().data_dir
        state = asyncio.run(execute(directory, live=args.live))
        path = directory / "energy" / state["run_id"] / "state.json"
        atomic_write(path, json.dumps(state, indent=2, ensure_ascii=False))
    except (ConfigurationError, ValidationError, ArtifactFailure, OSError, sqlite3.Error):
        print("Energy acquisition or storage failed; no successful acquisition is confirmed.")
        return 1
    output = {
        "execution_mode": "live_neso_with_fixture_planning" if args.live else "offline_fixture",
        "run_id": state["run_id"],
        "sources": list(state["source_records"].values()),
        "evidence": list(state["evidence_store"].values()),
        "errors": list(state["tool_errors"].values()),
        "state_path": str(path.resolve()),
        "report_generated": False,
        "limitations": "GB half-hour fuel shares; not absolute MWh or global output. "
        "Passages are a deterministic projection of retained API values.",
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 1 if state["tool_errors"] or not state["evidence_store"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
