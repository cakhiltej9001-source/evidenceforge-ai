"""Explicitly labeled offline planning demo; no live provider fallback."""

import argparse
import asyncio
import json

from pydantic import ValidationError

from evidenceforge.config import ConfigurationError, load_settings
from evidenceforge.schemas import ResearchRequest
from evidenceforge.services.planning import PlanningService


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline fixture planning demo (no retrieval).")
    parser.add_argument("question")
    parser.add_argument("--owner", default="local")
    parser.add_argument("--document", action="append", default=[])
    args = parser.parse_args()
    try:
        settings = load_settings()
        if settings.model_provider != "fixture":
            raise ConfigurationError(
                "This demo requires explicit fixture mode; no live adapter ran."
            )
        request = ResearchRequest(
            question=args.question,
            owner_scope=args.owner,
            document_ids=tuple(args.document),
        )
        state = asyncio.run(PlanningService().plan(request, settings.budget))
    except ConfigurationError as exc:
        print(str(exc))
        return 1
    except ValidationError:
        print("Invalid research request or planning configuration.")
        return 1
    output = {
        "execution_mode": "offline_fixture",
        "planning_status": state["planning_status"],
        "run_status": state["run_status"],
        "research_passes_completed": state["iteration_count"],
        "research_questions": state["research_questions"],
        "context_refs": state["context_refs"],
        "pending_queries": state["search_queries"],
        "events": sorted(state["events"].values(), key=lambda event: str(event["occurred_at"])),
        "errors": list(state["tool_errors"].values()),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 1 if state["planning_status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
