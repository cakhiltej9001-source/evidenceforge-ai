"""Offline deployment smoke with a durable record for separate-process reconnect."""

import argparse
import asyncio
import json
from pathlib import Path

from evidenceforge.energy_demo import execute
from evidenceforge.nodes.approval import PlanDecision
from evidenceforge.research import ResearchOptions
from evidenceforge.schemas import ResearchRequest
from evidenceforge.services.research import ResearchService, atomic_write


async def reconnect(directory: Path) -> dict[str, object]:
    record = json.loads((directory / "deployment-smoke.json").read_text(encoding="utf-8"))
    if record.get("mode") != "offline_fixture" or not isinstance(record.get("thread_id"), str):
        raise ValueError("Expected an offline deployment smoke record")
    service = ResearchService(directory)
    state = await service.snapshot(record["thread_id"])
    assert state["run_status"] == "completed"
    path = service.report_path(state)
    exported = json.loads(path.with_name("report.json").read_text(encoding="utf-8"))
    assert path.exists() and exported
    return {
        "mode": "offline_fixture",
        "separate_process_reconnect": "passed",
        "export": "passed",
        "provider_calls": 0,
        "run_id": state["run_id"],
    }


async def smoke(directory: Path) -> dict[str, object]:
    energy = await execute(directory / "source")
    assert energy["evidence_store"] and not energy["tool_errors"]
    assert all(
        source["provider"] == "carbon_intensity_fixture"
        for source in energy["source_records"].values()
    )
    first = ResearchService(directory, options=ResearchOptions(require_plan_approval=True))
    paused = await first.run(ResearchRequest(question="Compare solar and wind electricity output."))
    assert paused["run_status"] == "running" and paused["plan_version"] == 1
    second = ResearchService(directory, options=ResearchOptions(require_plan_approval=True))
    resumed = await second.resume(
        paused["thread_id"], decision=PlanDecision(approved=True, plan_version=1)
    )
    assert resumed["run_status"] == "completed"
    path = second.report_path(resumed)
    exported = json.loads(path.with_name("report.json").read_text(encoding="utf-8"))
    assert path.exists() and exported
    result = {
        "mode": "offline_fixture",
        "checkpoint_resume": "passed",
        "export": "passed",
        "energy_acquisition": "passed",
        "report": str(path.resolve()),
        "thread_id": paused["thread_id"],
        "provider_calls": 0,
    }
    atomic_write(directory / "deployment-smoke.json", json.dumps(result, indent=2) + "\n")
    await reconnect(directory)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--reconnect", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(reconnect(args.data_dir) if args.reconnect else smoke(args.data_dir))
    print(json.dumps(result, indent=2))
