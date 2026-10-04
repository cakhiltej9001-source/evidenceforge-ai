"""Offline evidence demo with a separate, explicit opt-in live smoke."""

import argparse
import asyncio
import json
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from evidenceforge.config import ConfigurationError, load_settings
from evidenceforge.graph.state import ResearchState
from evidenceforge.retrieval.contracts import ArtifactFailure
from evidenceforge.retrieval.tavily import TavilyAdapter
from evidenceforge.schemas import BudgetLimits, ResearchRequest, SourceType
from evidenceforge.services.retrieval import RetrievalService


async def execute(question: str, data_dir: Path | None, live: bool) -> ResearchState:
    settings = load_settings()
    if settings.model_provider != "fixture":
        raise ConfigurationError("Phase 3 requires fixture planning; no live model adapter ran.")
    request = ResearchRequest(question=question)
    directory = data_dir if data_dir is not None else settings.data_dir
    if not live:
        return await RetrievalService(directory).run(request, settings.budget)
    if settings.tavily_api_key is None:
        raise ConfigurationError(
            "--live requires EVIDENCEFORGE_TAVILY_API_KEY; no search was made."
        )
    adapter = TavilyAdapter(settings.tavily_api_key)
    try:
        # One search only for the explicit live smoke; planning remains an offline fixture.
        values = settings.budget.model_dump()
        values.update(max_subquestions=1, max_queries_per_pass=1, max_searches=1)
        return await RetrievalService(
            directory,
            {SourceType.WEB: adapter},
        ).run(request, BudgetLimits.model_validate(values))
    finally:
        await adapter.aclose()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 3 retained-evidence demo, no report generation."
    )
    parser.add_argument("question")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument(
        "--live", action="store_true", help="Opt in to one potentially billable Tavily search."
    )
    args = parser.parse_args()
    try:
        state = asyncio.run(execute(args.question, args.data_dir, args.live))
    except ConfigurationError as exc:
        print(str(exc))
        return 1
    except (ValidationError, ArtifactFailure, OSError, sqlite3.Error):
        print("Retrieval configuration or local storage failed; no report was produced.")
        return 1
    output = {
        "execution_mode": "live_tavily_with_fixture_planning" if args.live else "offline_fixture",
        "run_id": state["run_id"],
        "run_status": state["run_status"],
        "research_passes_completed": state["iteration_count"],
        "sources": list(state["source_records"].values()),
        "evidence": list(state["evidence_store"].values()),
        "rejections": list(state["rejected_evidence"].values()),
        "errors": list(state["tool_errors"].values()),
        "report_generated": False,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 1 if state["run_status"] == "failed" or state["tool_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
