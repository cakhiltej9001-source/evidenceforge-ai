"""CLI for durable local, provider-free research jobs."""

import argparse
import json
from pathlib import Path

from evidenceforge.config import load_settings
from evidenceforge.schemas import BudgetLimits, ResearchRequest
from evidenceforge.services.job_worker import process_one
from evidenceforge.storage.job_queue import JobQueue, JobQueueFailure


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--owner", default="local")
    commands = parser.add_subparsers(dest="command", required=True)
    enqueue = commands.add_parser("enqueue")
    enqueue.add_argument("question")
    enqueue.add_argument(
        "--demo", default="second-pass", choices=("immediate", "second-pass", "empty", "dispute")
    )
    commands.add_parser("worker", help="Process one queued offline job and exit.")
    status = commands.add_parser("status")
    status.add_argument("job")
    approve = commands.add_parser("approve")
    approve.add_argument("job")
    approve.add_argument("--plan-version", required=True, type=int)
    recover = commands.add_parser("recover", help="Explicitly continue an interrupted fixture job.")
    recover.add_argument("job")
    args = parser.parse_args()
    directory = args.data_dir or load_settings().data_dir
    queue = JobQueue(directory / "jobs")
    result: dict[str, object]
    try:
        if args.command == "enqueue":
            request = ResearchRequest(question=args.question, owner_scope=args.owner)
            result = {"job": queue.enqueue(request, args.demo, BudgetLimits())}
        elif args.command == "worker":
            result = {"job": process_one(directory, args.owner)}
        elif args.command == "approve":
            queue.continue_job(args.job, args.owner, plan_version=args.plan_version)
            result = {"job": args.job, "status": "queued"}
        elif args.command == "recover":
            if queue.get(args.job, args.owner)["status"] != "interrupted":
                raise JobQueueFailure("Only an interrupted fixture job can be recovered.")
            queue.continue_job(args.job, args.owner)
            result = {"job": args.job, "status": "queued"}
        else:
            row = queue.get(args.job, args.owner)
            result = {key: row[key] for key in ("id", "owner", "status", "thread", "error")}
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError):
        print(json.dumps({"error": "Offline job operation failed; check scope and checkpoint."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
